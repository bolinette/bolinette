import base64
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol

from bolinette.core import Cache, __user_cache__
from bolinette.core.exceptions import InitError
from bolinette.core.injection import Injection, init_method
from bolinette.core.types import Function, Type, TypeChecker
from bolinette.web import Payload, controller, post
from bolinette.web.auth import JwtClaims, NotSupportedTokenError
from bolinette.web.config import BlntAuthProps
from bolinette.web.exceptions import ForbiddenError

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
    from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes, PublicKeyTypes
    from cryptography.hazmat.primitives.ciphers.aead import AESCCM, AESGCM, AESGCMSIV, AESOCB3, AESSIV, ChaCha20Poly1305


class BlntAuthUserTransformer[InfoT, ClaimsT: dict[str, Any], PayloadT](Protocol):
    def check_user(self, payload: PayloadT, /) -> InfoT: ...
    def user_from_claims(self, claims: ClaimsT, /) -> InfoT: ...
    def user_to_claims(self, user_info: InfoT, /) -> ClaimsT: ...


class BolinetteJwt:
    def __init__(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token


class BlntAuthCryptoImports:
    def __init__(self) -> None:
        try:
            import cryptography.hazmat.primitives.asymmetric.rsa as rsa
            import cryptography.hazmat.primitives.ciphers.aead as aead
            import cryptography.hazmat.primitives.serialization as serialization
            import jwt
            import jwt.algorithms
            import jwt.exceptions
        except ImportError as err:
            raise InitError("Library pyjwt is not available, make sure to install it") from err
        self.jwt = jwt.PyJWT()
        self.jwt_errors = jwt.exceptions
        self.algorithms = jwt.algorithms
        self.serialization = serialization
        self.rsa = rsa
        self.aead = aead


class BolinetteAuthProvider:
    def __init__(self) -> None:
        self.paths: tuple[str, str]
        self.crypto = BlntAuthCryptoImports()
        self.transformer: BlntAuthUserTransformer[Any, dict[str, Any], Any]
        self.issuer: str
        self.audience: list[str]
        self.algorithm: str
        self.encode_key: str | bytes | PrivateKeyTypes | None
        self.passphrase: bytes | None
        self.decode_key: str | bytes | PublicKeyTypes | None
        self.encrypt_cipher: "AESGCM | ChaCha20Poly1305 | AESCCM | AESSIV | AESOCB3 | AESGCMSIV | None"
        self.cipher_aad: bytes | None

    @init_method
    def _init_props(self, props: BlntAuthProps) -> None:
        self.paths = (props.ctrl_path, props.route_path)

    @init_method
    def _init_transformer(self, cache: Cache, inject: Injection) -> None:
        classes = cache.get(
            BlntAuthUserTransformer,
            raises=False,
            hint=type[BlntAuthUserTransformer[Any, dict[str, Any], Any]],
        )
        if len(classes) < 1:
            raise InitError(f"Bolinette auth: no token transformer was registered with @{blnt_auth_user_transformer}")
        if len(classes) > 1:
            raise InitError("Bolinette auth: too many token transformer were registered")
        transformer_cls = classes[0]
        inject.add_singleton(BlntAuthUserTransformer, transformer_cls)
        inject.add_singleton(transformer_cls, transformer_cls)
        self.transformer = inject.require(transformer_cls)

    @init_method
    def _init_sign_method(self, config: "BlntAuthConfig") -> None:
        self.issuer = config.issuer
        self.audience = config.audience
        match config.signing.type:
            case "none":
                self.passphrase = None
                self.encode_key = None
                self.decode_key = None
            case "HS256" | "HS384" | "HS512":
                key = config.signing.key
                if key is None:
                    keyfile = config.signing.key_file
                    if keyfile is None:
                        raise InitError(
                            "Bolinette auth: HMAC algorithm must specify a "
                            "'key' or 'key_file' in the 'blntauth' config."
                        )
                    with open(Path(keyfile)) as f:
                        key = f.read()
                self.passphrase = None
                self.encode_key = self.decode_key = key
            case "RS256" | "RS384" | "RS512":
                self.passphrase = config.signing.passphrase
                if config.signing.private_key:
                    self.encode_key = self._load_private_pem_key(config.signing.private_key)
                elif config.signing.private_key_file:
                    self.encode_key = self._load_private_pem_key(Path(config.signing.private_key_file))
                elif config.signing.private_jwk_file:
                    self.encode_key = self._load_private_rsa_jwk_key(Path(config.signing.private_jwk_file))
                if self.encode_key is None:
                    raise InitError(
                        "Bolinette auth: RSA algorithm must specify a "
                        "'private_key, 'private_key_file' or 'private_jwk_file' in the 'blntauth' config."
                    )
                if config.signing.public_key:
                    self.decode_key = self._load_public_pem_key(config.signing.public_key)
                elif config.signing.public_key_file:
                    self.decode_key = self._load_public_pem_key(Path(config.signing.public_key_file))
                elif config.signing.public_jwk_file:
                    self.decode_key = self._load_public_rsa_jwk_key(Path(config.signing.public_jwk_file))
                if self.decode_key is None:
                    raise InitError(
                        "Bolinette auth: RSA algorithm must specify a "
                        "'public_key, 'public_key_file' or 'public_jwk_file' in the 'blntauth' config."
                    )
        self.algorithm = config.signing.type

    @init_method
    def _init_encrypt_method(self, config: "BlntAuthConfig") -> None:
        if config.encryption is None:
            self.encrypt_cipher = None
            self.cipher_aad = None
            return
        self.cipher_aad = config.encryption.associated_data
        match config.encryption.type:
            case "AESGCM":
                cipher_cls = self.crypto.aead.AESGCM
            case "ChaCha20Poly1305":
                cipher_cls = self.crypto.aead.ChaCha20Poly1305
            case "AESCCM":
                cipher_cls = self.crypto.aead.AESCCM
            case "AESSIV":
                cipher_cls = self.crypto.aead.AESSIV
            case "AESOCB3":
                cipher_cls = self.crypto.aead.AESOCB3
            case "AESGCMSIV":
                cipher_cls = self.crypto.aead.AESGCMSIV
        with open(Path(config.encryption.file), "rb") as f:
            key = f.read()
        self.encrypt_cipher = cipher_cls(key)

    @init_method
    def _init_auth_controller(self, cache: Cache) -> None:
        ctrl = self.get_login_controller()
        controller(self.paths[0], cache=cache)(ctrl)

    def _load_private_pem_key(self, key: bytes | Path) -> "PrivateKeyTypes":
        if isinstance(key, Path):
            with open(key, "rb") as f:
                key = f.read()
        return self.crypto.serialization.load_pem_private_key(key, self.passphrase)

    def _load_private_rsa_jwk_key(self, path: Path) -> "RSAPrivateKey":
        with open(path) as f:
            content = f.read()
        key = self.crypto.algorithms.RSAAlgorithm.from_jwk(content)
        if not isinstance(key, self.crypto.rsa.RSAPrivateKey):
            raise InitError(f"Bolinette auth: file {path} does not contain a private RSA JWK.")
        return key

    def _load_public_pem_key(self, key: bytes | Path) -> "PublicKeyTypes":
        if isinstance(key, Path):
            with open(key, "rb") as f:
                key = f.read()
        return self.crypto.serialization.load_pem_public_key(key, self.passphrase)

    def _load_public_rsa_jwk_key(self, path: Path) -> "RSAPublicKey":
        with open(path) as f:
            content = f.read()
        key = self.crypto.algorithms.RSAAlgorithm.from_jwk(content)
        if not isinstance(key, self.crypto.rsa.RSAPublicKey):
            raise InitError(f"Bolinette auth: file {path} does not contain a public RSA JWK.")
        return key

    def _create_token(
        self,
        type: str,
        issued_at: datetime,
        expires: datetime,
        additional_fields: dict[str, Any],
        payload: dict[str, Any],
    ) -> str:
        jwt = self.crypto.jwt.encode(
            {
                JwtClaims.Type: type,
                JwtClaims.IssuedAt: issued_at,
                JwtClaims.Expires: expires,
                JwtClaims.Issuer: self.issuer,
                JwtClaims.Audience: self.audience,
                **additional_fields,
                JwtClaims.Payload: payload,
            },
            self.encode_key,  # pyright: ignore[reportArgumentType]
            algorithm=self.algorithm,
        )
        if self.encrypt_cipher is None or self.cipher_aad is None:
            return jwt
        if isinstance(self.encrypt_cipher, self.crypto.aead.AESSIV):
            nonce = os.urandom(16)
            ct = self.encrypt_cipher.encrypt(jwt.encode(), [self.cipher_aad, nonce])
        else:
            nonce = os.urandom(12)
            ct = self.encrypt_cipher.encrypt(nonce, jwt.encode(), self.cipher_aad)
        return "blntauth:" + base64.b64encode(nonce + ct, altchars=b"_-").decode()

    def create_tokens(
        self,
        user_info: Any,
        fresh: bool = True,
        dt: datetime | None = None,
    ) -> BolinetteJwt:
        if dt is None:
            dt = datetime.now(UTC)
        payload = self.transformer.user_to_claims(user_info)
        return BolinetteJwt(
            self._create_token("access", dt, dt + timedelta(minutes=5), {"fresh": fresh}, payload),
            self._create_token("refresh", dt, dt + timedelta(days=30), {}, payload),
        )

    def validate(self, token: str) -> Any:
        token_b = token.encode()
        if self.encrypt_cipher is not None and self.cipher_aad is not None:
            if not token_b.startswith(b"blntauth:"):
                raise NotSupportedTokenError()
            token_b = token_b[len("blntauth:") :]
            token_b = base64.b64decode(token_b, altchars=b"_-")
            if isinstance(self.encrypt_cipher, self.crypto.aead.AESSIV):
                nonce, token_b = token_b[:16], token_b[16:]
                token_b = self.encrypt_cipher.decrypt(token_b, [self.cipher_aad, nonce])
            else:
                nonce, token_b = token_b[:12], token_b[12:]
                token_b = self.encrypt_cipher.decrypt(nonce, token_b, self.cipher_aad)
        try:
            if self.algorithm == "none":
                jwt_decode_args: dict[str, Any] = {"options": {"verify_signature": False}}
            else:
                jwt_decode_args = {"key": self.decode_key, "algorithms": [self.algorithm], "audience": self.audience}
            jwt: dict[str, Any] | Any = self.crypto.jwt.decode(jwt=token_b, **jwt_decode_args)
        except self.crypto.jwt_errors.PyJWTError as err:
            raise ForbiddenError(f"Invalid auth token: {', '.join(err.args)}", "auth.token.invalid") from err
        if (
            not TypeChecker.basic_check(jwt, dict[str, Any])
            or JwtClaims.Issuer not in jwt
            or jwt[JwtClaims.Issuer] != self.issuer
        ):
            raise NotSupportedTokenError()
        return self.transformer.user_from_claims(jwt.get(JwtClaims.Payload, {}))

    def get_login_controller(self) -> Any:
        payload_t: Type[Any] = Function(self.transformer.check_user).anno_at(0)
        super_self = self

        class BlntAuthLoginController:
            @post(super_self.paths[1])
            def login_route(
                self,
                payload: Annotated[payload_t.origin, Payload],  # pyright: ignore
                auth: BolinetteAuthProvider,
            ) -> dict[str, Any]:
                now = datetime.now(UTC)
                user_info = super_self.transformer.check_user(payload)
                tokens = auth.create_tokens(user_info, fresh=True, dt=now)
                return {
                    "access_token": tokens.access_token,
                    "refresh_token": tokens.refresh_token,
                }

        return BlntAuthLoginController


def blnt_auth_user_transformer[TransT: BlntAuthUserTransformer[Any, dict[str, Any], Any]](
    *, cache: Cache | None = None
) -> Callable[[type[TransT]], type[TransT]]:
    def decorator(func: type[TransT]) -> type[TransT]:
        (cache or __user_cache__).add(BlntAuthUserTransformer, func)
        return func

    return decorator


@dataclass(init=False)
class BlntAuthSignNoneConfig:
    type: Literal["none"]


@dataclass(init=False)
class BlntAuthSignHMACConfig:
    type: Literal["HS256", "HS384", "HS512"]
    key: str | None = None
    key_file: str | None = None


@dataclass(init=False)
class BlntAuthSignRSAConfig:
    type: Literal["RS256", "RS384", "RS512"]
    passphrase: bytes | None = None
    private_key: bytes | None = None
    private_key_file: str | None = None
    private_jwk_file: str | None = None
    public_key: bytes | None = None
    public_key_file: str | None = None
    public_jwk_file: str | None = None
    encrypt_tokens: Literal[False, "AESGCMSIV"] = False


@dataclass(init=False)
class BlntAuthEncryptConfig:
    type: Literal["AESGCM", "ChaCha20Poly1305", "AESCCM", "AESSIV", "AESOCB3", "AESGCMSIV"]
    file: str
    associated_data: bytes


@dataclass(init=False)
class BlntAuthConfig:
    issuer: str
    audience: list[str]
    signing: BlntAuthSignNoneConfig | BlntAuthSignHMACConfig | BlntAuthSignRSAConfig
    encryption: BlntAuthEncryptConfig | None
