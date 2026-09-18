import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from escondite import Cache

from bolinette.core import Bolinette, make_bolinette
from bolinette.core.exceptions import InitError
from bolinette.web import AsgiApplication, BlntAuthOptions, Controller, WebExtension, controller, get, with_middleware
from bolinette.web.auth import (
    Authenticated,
    AuthProvider,
    AuthProviders,
    BolinetteAuthProvider,
    JwtClaims,
    NotSupportedTokenError,
    auth_provider,
    blnt_auth_user_transformer,
)
from bolinette.web.exceptions import ForbiddenError, UnauthorizedError
from tests.web.conftest import AppFactory, AsgiClient, blnt_auth_env

HMAC_KEY = "0123456789abcdef0123456789abcdef"


class UserInfo:
    def __init__(self, name: str) -> None:
        self.name = name


def _transformer(cache: Cache) -> None:
    @blnt_auth_user_transformer(cache=cache)
    class Transformer:
        def check_user(self, payload: dict[str, Any], /) -> UserInfo:
            if payload.get("password") != "hunter2":
                raise UnauthorizedError("Bad credentials", "auth.bad_credentials")
            return UserInfo(str(payload["name"]))

        def user_from_claims(self, claims: dict[str, Any], /) -> UserInfo:
            return UserInfo(claims["name"])

        def user_to_claims(self, user_info: UserInfo, /) -> dict[str, Any]:
            return {"name": user_info.name}


def _me_controller(cache: Cache) -> None:
    @controller("me", cache=cache)
    class MeCtrl(Controller):
        @with_middleware(Authenticated)
        @get("")
        async def who(self, user: UserInfo) -> str:
            return user.name


async def _auth_app(cache: Cache, options: BlntAuthOptions | None = None) -> Bolinette:
    blnt = await make_bolinette(
        [WebExtension(blnt_auth=options if options is not None else BlntAuthOptions())],
        cache=cache,
    )
    await blnt.startup()
    return blnt


def _rsa_keys(tmp_cwd: Path, passphrase: bytes | None = None) -> tuple[Path, Path]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    encryption = serialization.BestAvailableEncryption(passphrase) if passphrase else serialization.NoEncryption()
    private = tmp_cwd / "private.pem"
    public = tmp_cwd / "public.pem"
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, encryption))
    public.write_bytes(
        key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    return private, public


def _rsa_jwks(tmp_cwd: Path) -> tuple[Path, Path]:
    import jwt.algorithms
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = tmp_cwd / "private.jwk.json"
    public = tmp_cwd / "public.jwk.json"
    private.write_text(json.dumps(jwt.algorithms.RSAAlgorithm.to_jwk(key, as_dict=True)))
    public.write_text(json.dumps(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)))
    return private, public


class _Provider:
    issuer = "custom"

    def validate(self, token: str) -> dict[str, Any]:
        if not token.startswith("custom:"):
            raise NotSupportedTokenError
        return {"name": token.removeprefix("custom:")}


class _UserProvider:
    issuer = "user"

    def validate(self, token: str) -> Any:
        return UserInfo(token.removeprefix("user:"))


class TestAuthProviders:
    async def test_without_any_provider(self, make_app: AppFactory) -> None:
        blnt = await make_app()
        providers = await blnt.injector.require(AuthProviders)

        assert await providers.get_providers() == {}
        with pytest.raises(UnauthorizedError) as raised:
            await providers.validate("anything")
        assert raised.value.error_code == "auth.token.unverified"

    async def test_a_cached_provider_is_used(self, make_app: AppFactory, cache: Cache) -> None:
        auth_provider(cache=cache)(_Provider)
        blnt = await make_app()
        providers = await blnt.injector.require(AuthProviders)

        assert await providers.validate("custom:bob") == {"name": "bob"}
        assert list(await providers.get_providers()) == ["custom"]

    async def test_an_unsupported_token_falls_through(self, make_app: AppFactory, cache: Cache) -> None:
        auth_provider(cache=cache)(_Provider)
        blnt = await make_app()
        providers = await blnt.injector.require(AuthProviders)

        with pytest.raises(UnauthorizedError):
            await providers.validate("other:bob")

    async def test_add_provider_registers_another_one(self, make_app: AppFactory) -> None:
        class Second:
            issuer = "second"

            def validate(self, token: str) -> dict[str, Any]:
                return {"from": "second"}

        blnt = await make_app()
        blnt.injector.services.add_singleton(Second)
        providers = await blnt.injector.require(AuthProviders)

        providers.add_provider(Second)
        providers.add_provider(Second)

        assert await providers.validate("x") == {"from": "second"}

    def test_the_protocol_shape(self) -> None:
        provider: AuthProvider = _Provider()

        assert provider.issuer == "custom"


class TestAuthenticatedMiddleware:
    async def test_missing_header(self, make_app: AppFactory, cache: Cache) -> None:
        _me_controller(cache)
        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        result = await client.request("GET", "/me")

        assert result.status == 401
        assert result.json()["errors"][0]["code"] == "unauthorized"

    async def test_bad_header_format(self, make_app: AppFactory, cache: Cache) -> None:
        _me_controller(cache)
        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        result = await client.request("GET", "/me", headers=[(b"authorization", b"Basic abc")])

        assert result.status == 400
        assert result.json()["errors"][0]["code"] == "auth.token.bad_format"

    async def test_the_user_info_reaches_the_route(self, make_app: AppFactory, cache: Cache) -> None:
        _me_controller(cache)
        auth_provider(cache=cache)(_UserProvider)
        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        result = await client.request("GET", "/me", headers=[(b"authorization", b"Bearer user:bob")])

        assert result.text == "bob"


class TestBolinetteAuthProvider:
    async def test_hmac_inline_key(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, f'type = "HS256"\nkey = "{HMAC_KEY}"')
        _transformer(cache)
        _me_controller(cache)
        blnt = await _auth_app(cache)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        tokens = (await client.json_request("POST", "/auth", {"name": "bob", "password": "hunter2"})).json()
        result = await client.request(
            "GET", "/me", headers=[(b"authorization", f"Bearer {tokens['access_token']}".encode())]
        )

        assert sorted(tokens) == ["access_token", "refresh_token"]
        assert result.text == "bob"
        await blnt.dispose()

    async def test_hmac_key_file(self, cache: Cache, env_folder: Path, tmp_cwd: Path) -> None:
        key_file = tmp_cwd / "hmac.key"
        key_file.write_text(HMAC_KEY)
        blnt_auth_env(env_folder, f'type = "HS256"\nkey_file = "{key_file}"')
        _transformer(cache)
        blnt = await _auth_app(cache)
        provider = await blnt.injector.require(BolinetteAuthProvider)

        assert provider.encode_key == HMAC_KEY
        await blnt.dispose()

    async def test_hmac_without_any_key(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, 'type = "HS256"')
        _transformer(cache)
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="HMAC algorithm"):
            await blnt.startup()

        await blnt.dispose()

    async def test_signing_none(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, 'type = "none"')
        _transformer(cache)
        blnt = await _auth_app(cache)
        provider = await blnt.injector.require(BolinetteAuthProvider)

        tokens = provider.create_tokens(UserInfo("bob"))

        assert provider.validate(tokens.access_token).name == "bob"
        await blnt.dispose()

    async def test_rsa_pem_files(self, cache: Cache, env_folder: Path, tmp_cwd: Path) -> None:
        private, public = _rsa_keys(tmp_cwd)
        blnt_auth_env(env_folder, f'type = "RS256"\nprivate_key_file = "{private}"\npublic_key_file = "{public}"')
        _transformer(cache)
        blnt = await _auth_app(cache)
        provider = await blnt.injector.require(BolinetteAuthProvider)

        tokens = provider.create_tokens(UserInfo("bob"))

        assert provider.validate(tokens.access_token).name == "bob"
        await blnt.dispose()

    async def test_rsa_inline_pem(self, cache: Cache, env_folder: Path, tmp_cwd: Path) -> None:
        private, public = _rsa_keys(tmp_cwd)
        private_pem = private.read_text().replace("\n", "\\n")
        public_pem = public.read_text().replace("\n", "\\n")
        blnt_auth_env(env_folder, f'type = "RS256"\nprivate_key = "{private_pem}"\npublic_key = "{public_pem}"')
        _transformer(cache)
        blnt = await _auth_app(cache)
        provider = await blnt.injector.require(BolinetteAuthProvider)

        assert provider.validate(provider.create_tokens(UserInfo("bob")).access_token).name == "bob"
        await blnt.dispose()

    async def test_rsa_with_a_passphrase(self, cache: Cache, env_folder: Path, tmp_cwd: Path) -> None:
        private, public = _rsa_keys(tmp_cwd, b"secret")
        blnt_auth_env(
            env_folder,
            f'type = "RS256"\npassphrase = "secret"\nprivate_key_file = "{private}"\npublic_key_file = "{public}"',
        )
        _transformer(cache)
        blnt = await _auth_app(cache)
        provider = await blnt.injector.require(BolinetteAuthProvider)

        assert provider.validate(provider.create_tokens(UserInfo("bob")).access_token).name == "bob"
        await blnt.dispose()

    async def test_rsa_jwk_files(self, cache: Cache, env_folder: Path, tmp_cwd: Path) -> None:
        private, public = _rsa_jwks(tmp_cwd)
        blnt_auth_env(env_folder, f'type = "RS256"\nprivate_jwk_file = "{private}"\npublic_jwk_file = "{public}"')
        _transformer(cache)
        blnt = await _auth_app(cache)
        provider = await blnt.injector.require(BolinetteAuthProvider)

        assert provider.validate(provider.create_tokens(UserInfo("bob")).access_token).name == "bob"
        await blnt.dispose()

    async def test_a_public_jwk_as_a_private_key_is_rejected(
        self, cache: Cache, env_folder: Path, tmp_cwd: Path
    ) -> None:
        _, public = _rsa_jwks(tmp_cwd)
        blnt_auth_env(env_folder, f'type = "RS256"\nprivate_jwk_file = "{public}"\npublic_jwk_file = "{public}"')
        _transformer(cache)
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="private RSA JWK"):
            await blnt.startup()

        await blnt.dispose()

    async def test_a_private_jwk_as_a_public_key_is_rejected(
        self, cache: Cache, env_folder: Path, tmp_cwd: Path
    ) -> None:
        private, _ = _rsa_jwks(tmp_cwd)
        blnt_auth_env(env_folder, f'type = "RS256"\nprivate_jwk_file = "{private}"\npublic_jwk_file = "{private}"')
        _transformer(cache)
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="public RSA JWK"):
            await blnt.startup()

        await blnt.dispose()

    async def test_rsa_without_a_private_key(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, 'type = "RS256"')
        _transformer(cache)
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="private_key"):
            await blnt.startup()

        await blnt.dispose()

    async def test_rsa_without_a_public_key(self, cache: Cache, env_folder: Path, tmp_cwd: Path) -> None:
        private, _ = _rsa_keys(tmp_cwd)
        blnt_auth_env(env_folder, f'type = "RS256"\nprivate_key_file = "{private}"')
        _transformer(cache)
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="public_key"):
            await blnt.startup()

        await blnt.dispose()


class TestTokenValidation:
    async def _provider(self, cache: Cache, env_folder: Path) -> BolinetteAuthProvider:
        blnt_auth_env(env_folder, f'type = "HS256"\nkey = "{HMAC_KEY}"')
        _transformer(cache)
        blnt = await _auth_app(cache)
        return await blnt.injector.require(BolinetteAuthProvider)

    async def test_claims_and_fixed_date(self, cache: Cache, env_folder: Path) -> None:
        import jwt

        provider = await self._provider(cache, env_folder)
        moment = datetime(2020, 1, 1, tzinfo=UTC)

        tokens = provider.create_tokens(UserInfo("bob"), fresh=False, dt=moment)
        decoded = jwt.decode(
            tokens.access_token,
            HMAC_KEY,
            algorithms=["HS256"],
            audience=["tests"],
            options={"verify_exp": False},
        )

        assert decoded[JwtClaims.Issuer] == "bolinette"
        assert decoded[JwtClaims.Type] == "access"
        assert decoded["fresh"] is False
        assert decoded[JwtClaims.IssuedAt] == int(moment.timestamp())
        assert decoded[JwtClaims.Expires] == int((moment + timedelta(minutes=5)).timestamp())

    async def test_a_garbage_token_is_forbidden(self, cache: Cache, env_folder: Path) -> None:
        provider = await self._provider(cache, env_folder)

        with pytest.raises(ForbiddenError) as raised:
            provider.validate("not.a.token")

        assert raised.value.error_code == "auth.token.invalid"

    async def test_an_expired_token_is_forbidden(self, cache: Cache, env_folder: Path) -> None:
        provider = await self._provider(cache, env_folder)
        tokens = provider.create_tokens(UserInfo("bob"), dt=datetime.now(UTC) - timedelta(days=1))

        with pytest.raises(ForbiddenError):
            provider.validate(tokens.access_token)

    async def test_another_issuer_is_not_supported(self, cache: Cache, env_folder: Path) -> None:
        import jwt

        provider = await self._provider(cache, env_folder)
        token = jwt.encode({JwtClaims.Issuer: "other", "aud": ["tests"]}, HMAC_KEY, algorithm="HS256")

        with pytest.raises(NotSupportedTokenError):
            provider.validate(token)

    async def test_a_token_without_an_issuer_is_not_supported(self, cache: Cache, env_folder: Path) -> None:
        import jwt

        provider = await self._provider(cache, env_folder)
        token = jwt.encode({"aud": ["tests"]}, HMAC_KEY, algorithm="HS256")

        with pytest.raises(NotSupportedTokenError):
            provider.validate(token)


class TestEncryption:
    @pytest.mark.parametrize(
        ("algo", "size"),
        [
            ("AESGCM", 128),
            ("ChaCha20Poly1305", None),
            ("AESCCM", 128),
            ("AESSIV", 256),
            ("AESOCB3", 128),
            ("AESGCMSIV", 128),
        ],
    )
    async def test_round_trip(self, cache: Cache, env_folder: Path, tmp_cwd: Path, algo: str, size: int | None) -> None:
        from cryptography.hazmat.primitives.ciphers import aead

        cipher_cls: Any = getattr(aead, algo)
        key = cipher_cls.generate_key(size) if size is not None else cipher_cls.generate_key()
        key_file = tmp_cwd / "key.aes"
        key_file.write_bytes(key)
        blnt_auth_env(
            env_folder,
            f'type = "HS256"\nkey = "{HMAC_KEY}"\n',
            f'\n[blntauth.encryption]\ntype = "{algo}"\nfile = "{key_file}"\nassociated_data = "blnt"\n',
        )
        _transformer(cache)
        blnt = await _auth_app(cache)
        provider = await blnt.injector.require(BolinetteAuthProvider)

        tokens = provider.create_tokens(UserInfo("bob"))

        assert tokens.access_token.startswith("blntauth:")
        assert provider.validate(tokens.access_token).name == "bob"
        await blnt.dispose()

    async def test_a_plain_token_is_not_supported_when_encryption_is_on(
        self, cache: Cache, env_folder: Path, tmp_cwd: Path
    ) -> None:
        from cryptography.hazmat.primitives.ciphers import aead

        key_file = tmp_cwd / "key.aes"
        key_file.write_bytes(aead.AESGCM.generate_key(128))
        blnt_auth_env(
            env_folder,
            f'type = "HS256"\nkey = "{HMAC_KEY}"\n',
            f'\n[blntauth.encryption]\ntype = "AESGCM"\nfile = "{key_file}"\nassociated_data = "blnt"\n',
        )
        _transformer(cache)
        blnt = await _auth_app(cache)
        provider = await blnt.injector.require(BolinetteAuthProvider)

        with pytest.raises(NotSupportedTokenError):
            provider.validate("plain.token.here")

        await blnt.dispose()


class TestTransformerLookup:
    async def test_no_transformer(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, f'type = "HS256"\nkey = "{HMAC_KEY}"')
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="no token transformer"):
            await blnt.startup()

        await blnt.dispose()

    async def test_two_transformers(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, f'type = "HS256"\nkey = "{HMAC_KEY}"')
        _transformer(cache)
        _transformer(cache)
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="too many token transformer"):
            await blnt.startup()

        await blnt.dispose()


class TestLoginController:
    async def test_custom_paths(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, f'type = "HS256"\nkey = "{HMAC_KEY}"')
        _transformer(cache)
        blnt = await _auth_app(cache, BlntAuthOptions("sessions", "login"))
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        result = await client.json_request("POST", "/sessions/login", {"name": "bob", "password": "hunter2"})

        assert sorted(result.json()) == ["access_token", "refresh_token"]
        assert (await client.json_request("POST", "/auth", {})).status == 404
        await blnt.dispose()

    async def test_bad_credentials(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, f'type = "HS256"\nkey = "{HMAC_KEY}"')
        _transformer(cache)
        blnt = await _auth_app(cache)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        result = await client.json_request("POST", "/auth", {"name": "bob", "password": "wrong"})

        assert result.status == 401
        assert result.json()["errors"][0]["code"] == "auth.bad_credentials"
        await blnt.dispose()

    async def test_a_bad_payload_is_reported(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, f'type = "HS256"\nkey = "{HMAC_KEY}"')

        @blnt_auth_user_transformer(cache=cache)
        class Transformer:
            def check_user(self, payload: "LoginPayload", /) -> UserInfo:
                return UserInfo(payload.name)

            def user_from_claims(self, claims: dict[str, Any], /) -> UserInfo:
                return UserInfo(claims["name"])

            def user_to_claims(self, user_info: UserInfo, /) -> dict[str, Any]:
                return {"name": user_info.name}

        blnt = await _auth_app(cache)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        result = await client.json_request("POST", "/auth", {})

        assert result.status == 400
        assert result.json()["errors"][0]["code"] == "payload.parameter.missing"
        await blnt.dispose()


from bolinette.core.mapping import BolinetteModel  # noqa: E402


class LoginPayload(BolinetteModel):
    name: str


class TestMissingLibrary:
    def test_the_crypto_imports_report_the_extra(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        from bolinette.web.auth._blntauth import BlntAuthCryptoImports

        monkeypatch.setitem(sys.modules, "jwt.algorithms", None)

        with pytest.raises(InitError, match=r"bolinette-web\[auth\]"):
            BlntAuthCryptoImports()
