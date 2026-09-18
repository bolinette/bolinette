import json
import os
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest
from escondite import Cache
from soupape import ServiceCollection
from sqlalchemy.orm import DeclarativeBase

from bolinette.api import ApiExtension
from bolinette.core import Bolinette, make_bolinette
from bolinette.core.extensions import Extension
from bolinette.data.relational import AsyncTransaction
from bolinette.web import AsgiApplication

type AppFactory = Callable[..., Coroutine[Any, Any, Bolinette]]
type ClientFactory = Callable[..., Coroutine[Any, Any, "AsgiClient"]]
type AsgiApp = Callable[[Any, Callable[[], Coroutine[Any, Any, Any]], Callable[[Any], Coroutine[Any, Any, None]]], Any]

DEFAULT_DATABASE = '[[data.databases]]\nname = "default"\nurl = "sqlite+aiosqlite://"\n'


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for marker in item.iter_markers("known_bug"):
            reason = marker.kwargs.get("reason") or (marker.args[0] if marker.args else "known bug")
            item.add_marker(pytest.mark.xfail(strict=True, reason=reason))


@pytest.fixture
def cache() -> Cache:
    return Cache()


@pytest.fixture
def tmp_cwd(tmp_path: Path) -> Iterator[Path]:
    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(original)


@pytest.fixture
def env_folder(tmp_cwd: Path) -> Path:
    folder = tmp_cwd / "env"
    folder.mkdir()
    return folder


@pytest.fixture
async def make_app(cache: Cache, env_folder: Path) -> AsyncIterator[AppFactory]:
    apps: list[Bolinette] = []

    async def factory(
        extensions: Sequence[Extension] | None = None,
        *,
        services: ServiceCollection | None = None,
        start: bool = True,
    ) -> Bolinette:
        if not (env_folder / "env.toml").exists():
            (env_folder / "env.toml").write_text(DEFAULT_DATABASE)
        blnt = await make_bolinette([ApiExtension(), *(extensions or ())], cache=cache, services=services)
        apps.append(blnt)
        if start:
            await blnt.startup()
        return blnt

    yield factory

    for blnt in reversed(apps):
        await blnt.dispose()


class HttpResult:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = messages

    @property
    def status(self) -> int:
        return next(m["status"] for m in self.messages if m["type"] == "http.response.start")

    @property
    def headers(self) -> dict[str, str]:
        start = next(m for m in self.messages if m["type"] == "http.response.start")
        return {k.decode().lower(): v.decode() for k, v in start.get("headers", [])}

    @property
    def body(self) -> bytes:
        return b"".join(m.get("body", b"") for m in self.messages if m["type"] == "http.response.body")

    @property
    def text(self) -> str:
        return self.body.decode()

    def json(self) -> Any:
        return json.loads(self.body)


class _NoMoreEventsError(Exception):
    pass


class AsgiClient:
    def __init__(self, blnt: Bolinette, app: AsgiApp) -> None:
        self.blnt = blnt
        self.app = app

    async def seed(self, *entities: DeclarativeBase, connection: str = "default") -> None:
        async with self.blnt.injector.get_scoped_injector() as scope:
            session = (await scope.require(AsyncTransaction)).get(connection)
            for entity in entities:
                session.add(entity)

    async def _run(self, scope: dict[str, Any], events: list[Any]) -> list[dict[str, Any]]:
        queue = list(events)
        sent: list[dict[str, Any]] = []

        async def receive() -> Any:
            if not queue:
                raise _NoMoreEventsError
            return queue.pop(0)

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        try:
            await self.app(scope, receive, send)
        except _NoMoreEventsError:  # pragma: no cover
            pass
        return sent

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: str = "",
        payload: Any = None,
        body: bytes | None = None,
    ) -> HttpResult:
        if payload is not None:
            body = json.dumps(payload).encode()
        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "path": path,
            "query_string": query.encode(),
            "headers": [],
        }
        return HttpResult(await self._run(scope, [{"type": "http.request", "body": body or b"", "more_body": False}]))

    async def get(self, path: str, **kwargs: Any) -> HttpResult:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, payload: Any = None, **kwargs: Any) -> HttpResult:
        return await self.request("POST", path, payload=payload, **kwargs)

    async def put(self, path: str, payload: Any = None, **kwargs: Any) -> HttpResult:
        return await self.request("PUT", path, payload=payload, **kwargs)

    async def patch(self, path: str, payload: Any = None, **kwargs: Any) -> HttpResult:
        return await self.request("PATCH", path, payload=payload, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> HttpResult:
        return await self.request("DELETE", path, **kwargs)


@pytest.fixture
def make_client(make_app: AppFactory) -> ClientFactory:
    async def factory(extensions: Sequence[Extension] | None = None) -> AsgiClient:
        blnt = await make_app(extensions)
        return AsgiClient(blnt, (await blnt.injector.require(AsgiApplication)).get_app())

    return factory
