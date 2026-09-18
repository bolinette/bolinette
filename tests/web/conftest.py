import json
import os
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest
from escondite import Cache
from soupape import ServiceCollection

from bolinette.core import Bolinette, make_bolinette
from bolinette.core.extensions import Extension
from bolinette.web import AsgiApplication, WebExtension

type AppFactory = Callable[..., Coroutine[Any, Any, Bolinette]]
type AsgiApp = Callable[[Any, Callable[[], Coroutine[Any, Any, Any]], Callable[[Any], Coroutine[Any, Any, None]]], Any]


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
        blnt = await make_bolinette([WebExtension(), *(extensions or ())], cache=cache, services=services)
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
    def started(self) -> bool:
        return any(m["type"] == "http.response.start" for m in self.messages)

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
    def __init__(self, app: AsgiApp) -> None:
        self.app = app

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
        except _NoMoreEventsError:
            pass
        return sent

    async def lifespan(self, *events: str) -> list[dict[str, Any]]:
        return await self._run(
            {"type": "lifespan", "asgi": {"version": "3.0"}},
            [{"type": event} for event in events],
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: str = "",
        headers: Sequence[tuple[bytes, bytes]] = (),
        body: bytes | None = None,
        chunks: Sequence[bytes] = (),
        events: Sequence[Any] | None = None,
    ) -> HttpResult:
        if events is None:
            if chunks:
                request_events: list[Any] = [
                    {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
                    for index, chunk in enumerate(chunks)
                ]
            else:
                request_events = [{"type": "http.request", "body": body or b"", "more_body": False}]
        else:
            request_events = list(events)
        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "path": path,
            "query_string": query.encode(),
            "headers": list(headers),
        }
        return HttpResult(await self._run(scope, request_events))

    async def json_request(self, method: str, path: str, payload: Any, **kwargs: Any) -> HttpResult:
        return await self.request(method, path, body=json.dumps(payload).encode(), **kwargs)

    async def websocket(self, *events: Any, path: str = "/ws") -> list[dict[str, Any]]:
        scope: dict[str, Any] = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "path": path,
            "query_string": b"",
            "headers": [],
        }
        return await self._run(scope, [*events, {"type": "websocket.disconnect", "code": 1000}])


def ws_message(payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": "websocket.receive", "text": json.dumps(payload)}


@pytest.fixture
async def web_client(make_app: AppFactory) -> AsgiClient:
    blnt = await make_app()
    return AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())


def write_env(env_folder: Path, content: str) -> None:
    (env_folder / "env.toml").write_text(content)


def blnt_auth_env(env_folder: Path, signing: str, encryption: str = "") -> None:
    write_env(
        env_folder,
        "[core]\ndebug = false\n\n"
        '[blntauth]\nissuer = "bolinette"\naudience = ["tests"]\n\n'
        f"[blntauth.signing]\n{signing}\n{encryption}",
    )
