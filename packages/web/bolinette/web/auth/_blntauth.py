import base64
import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol, cast

import pydantic
from escondite import Cache
from muotti import Mapper
from muotti.errors import ValidationError
from peritype import TWrap, wrap_func, wrap_type
from pydantic import Field
from soupape import AsyncInjector, ServiceCollection

from bolinette.core import startup
from bolinette.core.configuration import ConfigSection, Configuration, resolve_config_section
from bolinette.core.exceptions import InitError
from bolinette.core.mapping import BolinetteModel
from bolinette.web._config import BlntAuthOptions
from bolinette.web._resources import Payload, WebResources
from bolinette.web._resources._resolvers import build_payload_error
from bolinette.web._routing import Route
from bolinette.web.auth._jwt import JwtClaims
from bolinette.web.auth._provider import NotSupportedTokenError
from bolinette.web.exceptions import ForbiddenError

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
    from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes, PublicKeyTypes
    from cryptography.hazmat.primitives.ciphers.aead import AESCCM, AESGCM, AESGCMSIV, AESOCB3, AESSIV, ChaCha20Poly1305

BLNT_AUTH_SECTION_NAME = "blntauth"


class SigningNone(BolinetteModel):
    type: Literal["none"]


class SigningHmac(BolinetteModel):
    type: Literal["HS256", "HS384", "HS512"]
    key: str | None = None
    key_file: str | None = None


class SigningRsa(BolinetteModel):
    type: Literal["RS256", "RS384", "RS512"]
    passphrase: bytes | None = None
    private_key: bytes | None = None
    private_key_file: str | None = None
    private_jwk_file: str | None = None
    public_key: bytes | None = None
    public_key_file: str | None = None
    public_jwk_file: str | None = None


class EncryptionConfig(BolinetteModel):
    type: Literal["AESGCM", "ChaCha20Poly1305", "AESCCM", "AESSIV", "AESOCB3", "AESGCMSIV"]
    file: str
    associated_data: bytes


class BlntAuthSection(BolinetteModel):
    issuer: str
    audience: list[str]
    signing: SigningNone | SigningHmac | SigningRsa = Field(discriminator="type")
    encryption: EncryptionConfig | None = None


class BlntAuthUserTransformer[InfoT, ClaimsT: Mapping[str, Any], PayloadT](Protocol):
    def check_user(self, payload: PayloadT, /) -> InfoT: ...
    def user_from_claims(self, claims: ClaimsT, /) -> InfoT: ...
    def user_to_claims(self, user_info: InfoT, /) -> ClaimsT: ...


class BlntAuthUserTransformerMeta:
    KEY = "__blnt_web_auth_transformer__"


def blnt_auth_user_transformer[TransT: BlntAuthUserTransformer[Any, Any, Any]](
    *,
    cache: Cache | None = None,
) -> Callable[[type[TransT]], type[TransT]]:
    def decorator(cls: type[TransT]) -> type[TransT]:
        Cache.with_fallback(cache).add(BlntAuthUserTransformerMeta.KEY, cls)
        return cls

    return decorator


class BolinetteJwt:
    def __init__(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token


class BlntAuthCryptoImports:
    def __init__(self) -> None:
        try:
            import jwt
            import jwt.algorithms
            import jwt.exceptions
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives.ciphers import aead
        except ImportError as err:
            raise InitError("Library pyjwt is not available, install bolinette-web[auth]") from err
        self.jwt = jwt.PyJWT()
        self.jwt_errors = jwt.exceptions
        self.algorithms = jwt.algorithms
        self.serialization = serialization
        self.rsa = rsa
        self.aead = aead


def resolve_blnt_auth_section(configuration: Configuration) -> ConfigSection[BlntAuthSection]:
    if BLNT_AUTH_SECTION_NAME not in configuration.config:
        raise InitError(
            f"Bolinette auth: the '{BLNT_AUTH_SECTION_NAME}' configuration section is missing, "
            "it is required when the web extension is built with blnt_auth options"
        )
    try:
        return resolve_config_section(configuration, BlntAuthSection)
    except pydantic.ValidationError as err:
        raise InitError(f"Bolinette auth: invalid '{BLNT_AUTH_SECTION_NAME}' configuration section: {err}") from err


class BolinetteAuthProvider:
    def __init__(
        self,
        section: ConfigSection[BlntAuthSection],
        cache: Cache,
        injector: AsyncInjector,
        options: BlntAuthOptions,
    ) -> None:
        del injector
        config = section.value
        self.options = options
        self.crypto = BlntAuthCryptoImports()
        self.transformer: BlntAuthUserTransformer[Any, dict[str, Any], Any] = self._resolve_transformer(cache)
        self.login_payload_type: TWrap[Any] = wrap_func(self.transformer.check_user).get_signature_hint(0)
        self.issuer: str = config.issuer
        self.audience: list[str] = config.audience
        self.algorithm: str = config.signing.type
        self.passphrase: bytes | None = None
        self.encode_key: str | bytes | PrivateKeyTypes | None = None
        self.decode_key: str | bytes | PublicKeyTypes | None = None
        self.encrypt_cipher: AESGCM | ChaCha20Poly1305 | AESCCM | AESSIV | AESOCB3 | AESGCMSIV | None = None
        self.cipher_aad: bytes | None = None
        self._init_sign_method(config)
        self._init_encrypt_method(config)

    @staticmethod
    def _resolve_transformer(cache: Cache) -> "BlntAuthUserTransformer[Any, dict[str, Any], Any]":
        classes = list(
            cache.get(
                BlntAuthUserTransformerMeta.KEY,
                raises=False,
                hint=type[BlntAuthUserTransformer[Any, dict[str, Any], Any]],
            )
        )
        if len(classes) < 1:
            raise InitError(
                f"Bolinette auth: no token transformer was registered with @{blnt_auth_user_transformer.__name__}"
            )
        if len(classes) > 1:
            raise InitError("Bolinette auth: too many token transformer were registered")
        return classes[0]()

    def _init_sign_method(self, config: BlntAuthSection) -> None:
        match config.signing.type:
            case "none":
                pass
            case "HS256" | "HS384" | "HS512":
                signing_config = cast(SigningHmac, config.signing)
                key = signing_config.key
                if key is None:
                    keyfile = signing_config.key_file
                    if keyfile is None:
                        raise InitError(
                            "Bolinette auth: HMAC algorithm must specify a "
                            "'key' or 'key_file' in the 'blntauth' config."
                        )
                    with open(Path(keyfile)) as f:
                        key = f.read()
                self.encode_key = self.decode_key = key
            case "RS256" | "RS384" | "RS512":
                rsa_config = cast(SigningRsa, config.signing)
                self.passphrase = rsa_config.passphrase
                if rsa_config.private_key:
                    self.encode_key = self._load_private_pem_key(rsa_config.private_key)
                elif rsa_config.private_key_file:
                    self.encode_key = self._load_private_pem_key(Path(rsa_config.private_key_file))
                elif rsa_config.private_jwk_file:
                    self.encode_key = self._load_private_rsa_jwk_key(Path(rsa_config.private_jwk_file))
                if self.encode_key is None:
                    raise InitError(
                        "Bolinette auth: RSA algorithm must specify a "
                        "'private_key, 'private_key_file' or 'private_jwk_file' in the 'blntauth' config."
                    )
                if rsa_config.public_key:
                    self.decode_key = self._load_public_pem_key(rsa_config.public_key)
                elif rsa_config.public_key_file:
                    self.decode_key = self._load_public_pem_key(Path(rsa_config.public_key_file))
                elif rsa_config.public_jwk_file:
                    self.decode_key = self._load_public_rsa_jwk_key(Path(rsa_config.public_jwk_file))
                if self.decode_key is None:
                    raise InitError(
                        "Bolinette auth: RSA algorithm must specify a "
                        "'public_key, 'public_key_file' or 'public_jwk_file' in the 'blntauth' config."
                    )

    def _init_encrypt_method(self, config: BlntAuthSection) -> None:
        if config.encryption is None:
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

    def create_tokens(self, user_info: Any, fresh: bool = True, dt: datetime | None = None) -> BolinetteJwt:
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
                raise NotSupportedTokenError
            token_b = base64.b64decode(token_b[len("blntauth:") :], altchars=b"_-")
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
        if not isinstance(jwt, dict):
            raise NotSupportedTokenError
        claims: dict[str, Any] = jwt  # pyright: ignore[reportUnknownVariableType]
        if JwtClaims.Issuer not in claims or claims[JwtClaims.Issuer] != self.issuer:
            raise NotSupportedTokenError
        return self.transformer.user_from_claims(claims.get(JwtClaims.Payload, {}))


class _BlntAuthLoginController:
    async def login_route(
        self,
        payload: Annotated[dict[str, Any], Payload()],
        provider: BolinetteAuthProvider,
        mapper: Mapper,
        route: Route,
    ) -> dict[str, str]:
        required = provider.login_payload_type
        try:
            login_payload = mapper.map(dict[str, Any], required.nodes[0].origin, payload, validate=True)
        except ValidationError as err:
            raise build_payload_error(err, required, route) from err
        user_info = provider.transformer.check_user(login_payload)
        tokens = provider.create_tokens(user_info, fresh=True, dt=datetime.now(UTC))
        return {"access_token": tokens.access_token, "refresh_token": tokens.refresh_token}


async def _check_blnt_auth_provider(provider: BolinetteAuthProvider) -> None:
    del provider


async def _register_login_route(resources: WebResources, options: BlntAuthOptions) -> None:
    resources.add_route(
        wrap_type(_BlntAuthLoginController),
        options.controller_path,
        wrap_func(_BlntAuthLoginController.login_route),
        "POST",
        options.route_path,
    )


def register_blnt_auth(services: ServiceCollection, cache: Cache) -> None:
    services.add_singleton(resolve_blnt_auth_section)
    startup(cache=cache)(_check_blnt_auth_provider)
    for transformer_cls in cache.get(BlntAuthUserTransformerMeta.KEY, hint=type[Any], raises=False):
        services.add_singleton(transformer_cls)

    services.add_scoped(_BlntAuthLoginController)
    startup(cache=cache)(_register_login_route)
