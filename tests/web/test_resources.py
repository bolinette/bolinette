from typing import Awaitable, Callable

from aiohttp import web
from aiohttp.test_utils import TestClient

from bolinette.core import Cache
from bolinette.core.mapping import Mapper
from bolinette.core.mapping.mapper import (
    BoolTypeMapper,
    FloatTypeMapper,
    IntegerTypeMapper,
    StringTypeMapper,
    type_mapper,
)
from bolinette.core.testing import Mock
from bolinette.web import WebResources, controller, get, payload, post, route, with_middleware, without_middleware

ClientFixture = Callable[[web.Application], Awaitable[TestClient]]


def load_default_mappers(cache: Cache) -> None:
    type_mapper(int, cache=cache)(IntegerTypeMapper)
    type_mapper(str, cache=cache)(StringTypeMapper)
    type_mapper(float, cache=cache)(FloatTypeMapper)
    type_mapper(bool, cache=cache)(BoolTypeMapper)


async def test_call_basic_route(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    class _TestCtrl:
        @route("GET", "route")
        async def get_by_id(self) -> web.Response:
            return web.Response(status=200, body="ok")

    controller("test", cache=cache)(_TestCtrl)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test/route")

    assert resp.status == 200
    assert await resp.text() == "ok"


async def test_call_route_with_args(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    class _TestCtrl:
        @route("GET", "{id}")
        async def get_by_id(self, id: int) -> web.Response:
            return web.Response(status=200, body=f"{id}: {type(id)}")

    controller("test", cache=cache)(_TestCtrl)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test/42")

    assert resp.status == 200
    assert await resp.text() == f"42: {int}"


async def test_call_route_with_middleware(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    order: list[str] = []

    class _CtrlMdlw:
        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            order.append("ctrl")
            return await next()

    class _RouteMdlw1:
        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            order.append("route1")
            return await next()

    class _RouteMdlw2:
        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            order.append("route2")
            return await next()

    @controller("test", cache=cache)
    @with_middleware(_CtrlMdlw)
    class _:
        @route("GET", "")
        @with_middleware(_RouteMdlw1)
        @with_middleware(_RouteMdlw2)
        async def get_by_id(self) -> web.Response:
            return web.Response(status=200, body="ok")

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test")

    assert resp.status == 200
    assert await resp.text() == "ok"

    assert order == ["ctrl", "route1", "route2"]


async def test_remove_middleware_from_route(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    order: list[str] = []

    class _Mdlw1:
        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            order.append("1")
            return await next()

    class _Mdlw2:
        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            order.append("2")
            return await next()

    @controller("test", cache=cache)
    @with_middleware(_Mdlw1)
    @with_middleware(_Mdlw2)
    class _:
        @route("GET", "1")
        async def get1(self) -> web.Response:
            return web.Response(status=200, body="ok")

        @route("GET", "2")
        @without_middleware(_Mdlw1)
        async def get2(self) -> web.Response:
            return web.Response(status=200, body="ok")

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test/1")
    assert resp.status == 200
    assert await resp.text() == "ok"
    assert order == ["1", "2"]

    order.clear()
    resp = await client.get("/test/2")
    assert resp.status == 200
    assert await resp.text() == "ok"
    assert order == ["2"]


async def test_intercept_request(aiohttp_client: ClientFixture) -> None:
    class _Auth:
        def __init__(self, request: web.Request) -> None:
            self.request = request

        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            if "x" not in self.request.headers:
                return web.Response(status=401)
            return await next()

    cache = Cache()

    @controller("test", cache=cache)
    @with_middleware(_Auth)
    class _:
        @get("")
        async def get_by_id(self) -> web.Response:
            return web.Response(status=200, body="ok")

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test")

    assert resp.status == 401


async def test_return_mapped_json(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    class Entity:
        def __init__(self, id: int, name: str) -> None:
            self.id = id
            self.name = name

    class EntityResponse:
        id: int
        name: str

    @controller("entity", cache=cache)
    class _:
        def __init__(self, mapper: Mapper) -> None:
            self.mapper = mapper

        @get("{id}/{name}")
        async def get_entity(self, id: int, name: str) -> EntityResponse:
            entity = Entity(id, name)
            return self.mapper.map(Entity, EntityResponse, entity)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    load_default_mappers(cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/entity/1/test")

    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"id": 1, "name": "test"}


async def test_expect_payload_return_status(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    class Entity:
        def __init__(self, id: int, name: str) -> None:
            self.id = id
            self.name = name

    class EntityPayload:
        id: int
        name: str

    class EntityResponse:
        id: int
        name: str

    @controller("entity", cache=cache)
    class _:
        def __init__(self, mapper: Mapper) -> None:
            self.mapper = mapper

        @post("")
        async def create_entity(self, payload: EntityPayload = payload()) -> tuple[EntityResponse, int]:
            entity = Entity(payload.id, payload.name)
            return self.mapper.map(Entity, EntityResponse, entity), 201

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    load_default_mappers(cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.post("/entity", json={"id": 1, "name": "test"})

    assert resp.status == 201
    assert resp.content_type == "application/json"
    assert await resp.json() == {"id": 1, "name": "test"}


async def test_nullable_payload(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    class Payload:
        value: str

    @controller("entity", cache=cache)
    class _:
        def __init__(self, mapper: Mapper) -> None:
            self.mapper = mapper

        @post("")
        async def create_entity(self, payload: Payload | None = payload()) -> str:
            return "<none>" if not payload else payload.value

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    load_default_mappers(cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.post("/entity")

    assert resp.status == 200
    assert resp.content_type == "text/plain"
    assert await resp.text() == "<none>"


async def test_fail_non_nullable_payload(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    class Payload:
        value: str

    @controller("entity", cache=cache)
    class _:
        def __init__(self, mapper: Mapper) -> None:
            self.mapper = mapper

        @post("")
        async def create_entity(self, payload: Payload = payload()) -> str:
            return payload.value

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    load_default_mappers(cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.post("/entity")

    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == {
        "code": 400,
        "status": "Bad Request",
        "error": {
            "code": "web.payload.expected",
            "message": "Route test_fail_non_nullable_payload.<locals>._.create_entity, "
            "Payload expected but none provided",
            "params": {},
        },
    }
