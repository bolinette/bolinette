import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import aiohttp
import pytest

from bolinette.core import Cache
from bolinette.core.bolinette import InitError
from bolinette.core.testing import with_tmp_cwd_async
from bolinette.core.utils.strings import indent
from bolinette.web import controller, get, with_middleware
from bolinette.web.auth import Authenticated, blnt_auth_user_transformer
from bolinette.web.extension import WebExtension
from tests.bolinette.web_utils import run_test_server

CRYPTO_INSTALLED = importlib.util.find_spec("cryptography") is not None


class UserLoginPayload(TypedDict):
    username: str
    password: str


class UserTokenClaims(TypedDict):
    username: str


@dataclass
class User:
    id: int
    username: str
    password: str


USER_STORE = [
    User(id=1, username="bob", password="bobspassword"),
    User(id=2, username="alice", password="alicespassword"),
    User(id=3, username="charlie", password="charliespassword"),
    User(id=4, username="dave", password="davespassword"),
]


class TestUserTransformer:
    def check_user(self, payload: UserLoginPayload, /) -> User:
        for user in USER_STORE:
            if user.username == payload["username"] and user.password == payload["password"]:
                return user
        raise ValueError("Invalid username or password")

    def user_from_claims(self, claims: UserTokenClaims, /) -> User:
        for user in USER_STORE:
            if user.username == claims["username"]:
                return user
        raise ValueError("User not found")

    def user_to_claims(self, user_info: User, /) -> UserTokenClaims:
        return {"username": user_info.username}


@with_middleware(Authenticated)
class _TestController:
    @get("")
    async def test(self) -> str:
        return "Hello, world!"


def _activate_auth_callback(ext: WebExtension) -> None:
    ext.use_blnt_auth()


async def _test_request_callback(session: aiohttp.ClientSession, username: str, password: str) -> None:
    async with session.get("/") as response:
        assert response.status == 401

    async with session.post("/auth", json={"username": username, "password": password}) as response:
        assert response.status == 200
        data = await response.json()
        assert "access_token" in data

    async with session.get("/", headers={"Authorization": f"Bearer {data['access_token']}"}) as response:
        assert response.status == 200
        text = await response.text()
        assert text == "Hello, world!"


def _generate_rsa_key_pair(passphrase: bytes | None = None) -> tuple[bytes, bytes]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=(
            serialization.BestAvailableEncryption(passphrase) if passphrase else serialization.NoEncryption()
        ),
    )
    public_key = private_key.public_key()
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return pem_private, pem_public


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@with_tmp_cwd_async
async def test_login_with_hmac() -> None:
    env_dir = Path("env")
    env_dir.mkdir(exist_ok=True, parents=True)
    with open(env_dir / "env.yaml", "w") as f:
        f.write("""blntauth:
    issuer: bolinette_test
    audience: bolinette_test
    signing:
        type: HS512
        key: testkey""")

    cache = Cache()

    blnt_auth_user_transformer(cache=cache)(TestUserTransformer)
    controller("/", cache=cache)(_TestController)

    await run_test_server(
        cache,
        lambda s: _test_request_callback(s, "bob", "bobspassword"),
        _activate_auth_callback,
    )


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@with_tmp_cwd_async
async def test_login_with_rsa() -> None:
    pem_private, pem_public = _generate_rsa_key_pair()

    env_dir = Path("env")
    env_dir.mkdir(exist_ok=True, parents=True)
    with open(env_dir / "env.yaml", "w") as f:
        f.write(f"""blntauth:
  issuer: bolinette_test
  audience: bolinette_test
  signing:
    type: RS512
    private_key: |-
      {indent(pem_private.decode("utf-8"), 6, skip_first=True)}
    public_key: |-
      {indent(pem_public.decode("utf-8"), 6, skip_first=True)}""")

    cache = Cache()

    blnt_auth_user_transformer(cache=cache)(TestUserTransformer)
    controller("/", cache=cache)(_TestController)

    await run_test_server(
        cache,
        lambda s: _test_request_callback(s, "alice", "alicespassword"),
        _activate_auth_callback,
    )


@pytest.mark.skipif(not CRYPTO_INSTALLED, reason="Cryptography is not installed")
@with_tmp_cwd_async
async def test_fail_init_server_no_auth_transformer() -> None:
    env_dir = Path("env")
    env_dir.mkdir(exist_ok=True, parents=True)
    with open(env_dir / "env.yaml", "w") as f:
        f.write("""blntauth:
    issuer: bolinette_test
    audience: bolinette_test
    signing:
        type: HS512
        key: testkey""")

    cache = Cache()

    controller("/", cache=cache)(_TestController)

    with pytest.raises(InitError) as info:
        await run_test_server(
            cache,
            lambda s: _test_request_callback(s, "bob", "bobspassword"),
            _activate_auth_callback,
        )

    assert info.value.message == "Bolinette auth: no token transformer was registered with @blnt_auth_user_transformer"
