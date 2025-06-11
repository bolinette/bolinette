import importlib
import importlib.util
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from bolinette.core import Cache
from bolinette.core.testing import Mock, with_tmp_cwd_async
from bolinette.web.auth import BolinetteAuthProvider, blnt_auth_user_transformer
from bolinette.web.auth.blntauth import BlntAuthConfig
from bolinette.web.commands import new_rsa_key
from bolinette.web.config import BlntAuthProps
from bolinette.web.resources import WebResources

CRYPTO_INSTALLED = importlib.util.find_spec("cryptography") is not None
JWT_INSTALLED = importlib.util.find_spec("jwt")


@dataclass
class _LoginPayload:
    username: str
    password: str


@dataclass
class _User:
    username: str
    password: str


_user = _User("bob", "password")


class _CustomUserTransformer:
    def check_user(self, payload: _LoginPayload) -> _User: ...

    def user_from_claims(self, claims: dict[str, Any]) -> _User:
        assert claims["username"] == "bob"
        return _user

    def user_to_claims(self, user: _User) -> dict[str, Any]:
        return {"username": user.username}


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@pytest.mark.skipif(not JWT_INSTALLED, reason="PyJWT is not installed")
def test_blntauth_generate_tokens() -> None:
    import jwt

    def mock_add_controller(ctrl_cls: type, path: str) -> None: ...

    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(WebResources).setup(lambda wr: wr.add_controller, mock_add_controller)
    mock.mock(BlntAuthProps).setup(lambda p: p.ctrl_path, "auth").setup(lambda p: p.route_path, "")
    (
        mock.mock(BlntAuthConfig)
        .setup(lambda c: c.issuer, "test_iss")
        .setup(lambda c: c.audience, "test_aud")
        .setup(lambda c: c.signing, SimpleNamespace(type="none"))
        .setup(lambda c: c.encryption, None)
    )
    mock.injection.add_singleton(BolinetteAuthProvider)

    blnt_auth_user_transformer(cache=cache)(_CustomUserTransformer)

    blntauth = mock.injection.require(BolinetteAuthProvider)

    token = blntauth.create_tokens(_user)

    decoded_user = blntauth.validate(token.access_token)
    assert isinstance(decoded_user, _User)
    assert decoded_user.username == "bob"

    decoded_token = jwt.decode(token.access_token, options={"verify_signature": False})
    assert isinstance(decoded_token, dict)
    assert decoded_token["payload"]["username"] == "bob"


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@pytest.mark.skipif(not JWT_INSTALLED, reason="PyJWT is not installed")
async def test_blnt_token_with_hmac() -> None:
    import jwt

    def mock_add_controller(ctrl_cls: type, path: str) -> None: ...

    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(WebResources).setup(lambda wr: wr.add_controller, mock_add_controller)
    mock.mock(BlntAuthProps).setup(lambda p: p.ctrl_path, "auth").setup(lambda p: p.route_path, "")
    (
        mock.mock(BlntAuthConfig)
        .setup(lambda c: c.issuer, "test_iss")
        .setup(lambda c: c.audience, "test_aud")
        .setup(
            lambda c: c.signing,
            SimpleNamespace(
                type="HS512",
                key=b"testkey",
                key_file=None,
            ),
        )
        .setup(lambda c: c.encryption, None)
    )
    mock.injection.add_singleton(BolinetteAuthProvider)

    blnt_auth_user_transformer(cache=cache)(_CustomUserTransformer)

    blntauth = mock.injection.require(BolinetteAuthProvider)

    token = blntauth.create_tokens(_user)

    decoded_user = blntauth.validate(token.access_token)
    assert isinstance(decoded_user, _User)
    assert decoded_user.username == "bob"

    decoded_token = jwt.decode(token.access_token, options={"verify_signature": False})
    assert isinstance(decoded_token, dict)
    assert decoded_token["payload"]["username"] == "bob"


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@pytest.mark.skipif(not JWT_INSTALLED, reason="PyJWT is not installed")
@with_tmp_cwd_async
async def test_blnt_token_with_hmac_in_file() -> None:
    import jwt

    def mock_add_controller(ctrl_cls: type, path: str) -> None: ...

    with open("testkey.txt", "wb") as f:
        f.write(b"testkey")

    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(WebResources).setup(lambda wr: wr.add_controller, mock_add_controller)
    mock.mock(BlntAuthProps).setup(lambda p: p.ctrl_path, "auth").setup(lambda p: p.route_path, "")
    (
        mock.mock(BlntAuthConfig)
        .setup(lambda c: c.issuer, "test_iss")
        .setup(lambda c: c.audience, "test_aud")
        .setup(
            lambda c: c.signing,
            SimpleNamespace(
                type="HS512",
                key=None,
                key_file="testkey.txt",
            ),
        )
        .setup(lambda c: c.encryption, None)
    )
    mock.injection.add_singleton(BolinetteAuthProvider)

    blnt_auth_user_transformer(cache=cache)(_CustomUserTransformer)

    blntauth = mock.injection.require(BolinetteAuthProvider)

    token = blntauth.create_tokens(_user)

    decoded_user = blntauth.validate(token.access_token)
    assert isinstance(decoded_user, _User)
    assert decoded_user.username == "bob"

    decoded_token = jwt.decode(token.access_token, options={"verify_signature": False})
    assert isinstance(decoded_token, dict)
    assert decoded_token["payload"]["username"] == "bob"


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@pytest.mark.skipif(not JWT_INSTALLED, reason="PyJWT is not installed")
@with_tmp_cwd_async
async def test_blnt_token_with_rsa_in_file() -> None:
    import jwt

    def mock_add_controller(ctrl_cls: type, path: str) -> None: ...

    await new_rsa_key(outdir="", keyname="testkey", passphrase=b"testpass")

    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(WebResources).setup(lambda wr: wr.add_controller, mock_add_controller)
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
                private_key_file="testkey.pem",
                private_jwk_file=None,
                public_key=None,
                public_key_file="testkey.pem.pub",
                public_jwk_file=None,
                encrypt_tokens=None,
            ),
        )
        .setup(lambda c: c.encryption, None)
    )
    mock.injection.add_singleton(BolinetteAuthProvider)

    blnt_auth_user_transformer(cache=cache)(_CustomUserTransformer)

    blntauth = mock.injection.require(BolinetteAuthProvider)

    token = blntauth.create_tokens(_user)

    decoded_user = blntauth.validate(token.access_token)
    assert isinstance(decoded_user, _User)
    assert decoded_user.username == "bob"

    decoded_token = jwt.decode(token.access_token, options={"verify_signature": False})
    assert isinstance(decoded_token, dict)
    assert decoded_token["payload"]["username"] == "bob"


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@pytest.mark.skipif(not JWT_INSTALLED, reason="PyJWT is not installed")
@with_tmp_cwd_async
async def test_blnt_token_with_rsa_in_jwk_file() -> None:
    import jwt

    def mock_add_controller(ctrl_cls: type, path: str) -> None: ...

    await new_rsa_key(outdir="", keyname="testkey", passphrase=b"testpass", jwk=True)

    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(WebResources).setup(lambda wr: wr.add_controller, mock_add_controller)
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
                private_key_file=None,
                private_jwk_file="testkey.private.jwk.json",
                public_key=None,
                public_key_file=None,
                public_jwk_file="testkey.public.jwk.json",
                encrypt_tokens=None,
            ),
        )
        .setup(lambda c: c.encryption, None)
    )
    mock.injection.add_singleton(BolinetteAuthProvider)

    blnt_auth_user_transformer(cache=cache)(_CustomUserTransformer)

    blntauth = mock.injection.require(BolinetteAuthProvider)

    token = blntauth.create_tokens(_user)

    decoded_user = blntauth.validate(token.access_token)
    assert isinstance(decoded_user, _User)
    assert decoded_user.username == "bob"

    decoded_token = jwt.decode(token.access_token, options={"verify_signature": False})
    assert isinstance(decoded_token, dict)
    assert decoded_token["payload"]["username"] == "bob"


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@pytest.mark.skipif(not JWT_INSTALLED, reason="PyJWT is not installed")
@with_tmp_cwd_async
async def test_blnt_token_with_rsa_in_config() -> None:
    import jwt

    def mock_add_controller(ctrl_cls: type, path: str) -> None: ...

    await new_rsa_key(outdir="", keyname="testkey")
    with open("testkey.pem", "rb") as f:
        private_key = f.read()
    with open("testkey.pem.pub", "rb") as f:
        public_key = f.read()

    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(WebResources).setup(lambda wr: wr.add_controller, mock_add_controller)
    mock.mock(BlntAuthProps).setup(lambda p: p.ctrl_path, "auth").setup(lambda p: p.route_path, "")
    (
        mock.mock(BlntAuthConfig)
        .setup(lambda c: c.issuer, "test_iss")
        .setup(lambda c: c.audience, "test_aud")
        .setup(
            lambda c: c.signing,
            SimpleNamespace(
                type="RS512",
                passphrase=None,
                private_key=private_key,
                private_key_file=None,
                private_jwk_file=None,
                public_key=public_key,
                public_key_file=None,
                public_jwk_file=None,
                encrypt_tokens=None,
            ),
        )
        .setup(lambda c: c.encryption, None)
    )
    mock.injection.add_singleton(BolinetteAuthProvider)

    blnt_auth_user_transformer(cache=cache)(_CustomUserTransformer)

    blntauth = mock.injection.require(BolinetteAuthProvider)

    token = blntauth.create_tokens(_user)

    decoded_user = blntauth.validate(token.access_token)
    assert isinstance(decoded_user, _User)
    assert decoded_user.username == "bob"

    decoded_token = jwt.decode(token.access_token, options={"verify_signature": False})
    assert isinstance(decoded_token, dict)
    assert decoded_token["payload"]["username"] == "bob"
