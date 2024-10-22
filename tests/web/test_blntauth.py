import importlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

import pytest

from bolinette.core import Cache
from bolinette.core.testing import Mock
from bolinette.web.auth import BolinetteAuthProvider, blnt_auth_user_transformer
from bolinette.web.auth.blntauth import BlntAuthConfig
from bolinette.web.commands import new_rsa_key
from bolinette.web.config import BlntAuthProps

JWT_INSTALLED = importlib.util.find_spec("jwt")


@pytest.mark.skipif(not JWT_INSTALLED, reason="PyJWT is not installed")
def test_blntauth_generate_tokens() -> None:
    import jwt

    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(BlntAuthProps).setup(lambda p: p.ctrl_path, "auth").setup(lambda p: p.route_path, "")
    (
        mock.mock(BlntAuthConfig)
        .setup(lambda c: c.issuer, "test_iss")
        .setup(lambda c: c.audience, "test_aud")
        .setup(lambda c: c.signing, SimpleNamespace(type="none"))
        .setup(lambda c: c.encryption, None)
    )
    mock.injection.add_singleton(BolinetteAuthProvider)

    @dataclass(init=False)
    class LoginPayload:
        username: str
        password: str

    @dataclass()
    class User:
        username: str
        password: str

    user = User("bob", "password")
    order: list[str] = []

    class CustomUserTransformer:
        def check_user(self, payload: LoginPayload) -> User: ...

        def user_from_claims(self, claims: dict[str, Any]) -> User:
            order.append("from_claims")
            assert claims["username"] == "bob"
            return user

        def user_to_claims(self, user: User) -> dict[str, Any]:
            order.append("to_claims")
            return {"username": user.username}

    blnt_auth_user_transformer(cache=cache)(CustomUserTransformer)

    blntauth = mock.injection.require(BolinetteAuthProvider)

    token = blntauth.create_tokens(user)

    decoded_user = blntauth.validate(token.access_token)
    assert isinstance(decoded_user, User)
    assert decoded_user.username == "bob"
    assert order == ["to_claims", "from_claims"]

    decoded_token = jwt.decode(token.access_token, options={"verify_signature": False})
    assert isinstance(decoded_token, dict)
    assert decoded_token["payload"]["username"] == "bob"


@pytest.mark.skipif(not JWT_INSTALLED, reason="PyJWT is not installed")
async def test_blnt_token_with_rsa() -> None:
    import jwt

    with TemporaryDirectory() as tmp_dir:
        await new_rsa_key(outdir=str(Path(tmp_dir)), passphrase=b"testpass")

        cache = Cache()
        mock = Mock(cache=cache)
        mock.mock(BlntAuthProps).setup(lambda p: p.ctrl_path, "auth").setup(lambda p: p.route_path, "")
        (
            mock.mock(BlntAuthConfig)
            .setup(lambda c: c.issuer, "test_iss")
            .setup(lambda c: c.audience, "test_aud")
            .setup(
                lambda c: c.signing,
                SimpleNamespace(
                    type="RS512",
                    passphrase=b"testpass",
                    private_key=None,
                    private_key_file=str(Path(tmp_dir, "sign.pem")),
                    private_jwk_file=None,
                    public_key=None,
                    public_key_file=str(Path(tmp_dir, "sign.pem.pub")),
                    public_jwk_file=None,
                    encrypt_tokens=None,
                ),
            )
            .setup(lambda c: c.encryption, None)
        )
        mock.injection.add_singleton(BolinetteAuthProvider)

        @dataclass(init=False)
        class LoginPayload:
            username: str
            password: str

        @dataclass()
        class User:
            username: str
            password: str

        user = User("bob", "password")
        order: list[str] = []

        class CustomUserTransformer:
            def check_user(self, payload: LoginPayload) -> User: ...

            def user_from_claims(self, claims: dict[str, Any]) -> User:
                order.append("from_claims")
                assert claims["username"] == "bob"
                return user

            def user_to_claims(self, user: User) -> dict[str, Any]:
                order.append("to_claims")
                return {"username": user.username}

        blnt_auth_user_transformer(cache=cache)(CustomUserTransformer)

        blntauth = mock.injection.require(BolinetteAuthProvider)

        token = blntauth.create_tokens(user)

        decoded_user = blntauth.validate(token.access_token)
        assert isinstance(decoded_user, User)
        assert decoded_user.username == "bob"
        assert order == ["to_claims", "from_claims"]

        decoded_token = jwt.decode(token.access_token, options={"verify_signature": False})
        assert isinstance(decoded_token, dict)
        assert decoded_token["payload"]["username"] == "bob"
