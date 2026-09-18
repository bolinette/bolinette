from collections.abc import Awaitable, Callable
from typing import Any

from escondite import Cache
from peritype import wrap_type

from bolinette.core import meta
from bolinette.web import AsgiApplication, Controller, Middleware, controller, get, with_middleware, without_middleware
from bolinette.web._middleware import MiddlewareBag
from bolinette.web.exceptions import ForbiddenError
from tests.web.conftest import AppFactory, AsgiClient

CALLS: list[str] = []


class Tracer:
    def options(self, tag: str = "tracer") -> None:
        self.tag = tag

    async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any:
        CALLS.append(f"in:{self.tag}")
        result = await next()
        CALLS.append(f"out:{self.tag}")
        return result


class Blocker:
    def options(self) -> None:
        pass

    async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any:
        return "blocked"


class Failer:
    def options(self) -> None:
        pass

    async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any:
        raise ForbiddenError("nope", "test.blocked")


def _bag(obj: Any) -> MiddlewareBag:
    return meta.get(obj, MiddlewareBag.KEY)


async def _client(make_app: AppFactory) -> AsgiClient:
    blnt = await make_app()
    return AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())


class TestMiddlewareDecorators:
    def test_with_middleware_fills_the_bag(self) -> None:
        @with_middleware(Tracer, "a")
        def handler() -> None:
            pass

        bag = _bag(handler)

        assert list(bag.added) == [wrap_type(Tracer)]
        assert bag.added[wrap_type(Tracer)].args == ("a",)
        assert bag.added[wrap_type(Tracer)].kwargs == {}
        assert bag.removed == []

    def test_keyword_options_are_kept(self) -> None:
        @with_middleware(Tracer, tag="kw")
        def handler() -> None:
            pass

        assert _bag(handler).added[wrap_type(Tracer)].kwargs == {"tag": "kw"}

    def test_without_middleware_fills_the_bag(self) -> None:
        @without_middleware(Blocker)
        def handler() -> None:
            pass

        assert _bag(handler).removed == [wrap_type(Blocker)]

    def test_both_decorators_share_one_bag(self) -> None:
        @with_middleware(Tracer)
        @without_middleware(Blocker)
        def handler() -> None:
            pass

        bag = _bag(handler)

        assert list(bag.added) == [wrap_type(Tracer)]
        assert bag.removed == [wrap_type(Blocker)]

    def test_middleware_protocol_is_satisfied(self) -> None:
        middleware: Middleware[...] = Tracer()

        assert middleware.options is not None


class TestMiddlewareExecution:
    async def test_controller_middleware_wraps_every_route(self, make_app: AppFactory, cache: Cache) -> None:
        CALLS.clear()

        @with_middleware(Tracer, "ctrl")
        @controller("items", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> str:
                CALLS.append("route")
                return "ok"

        client = await _client(make_app)
        result = await client.request("GET", "/items")

        assert result.text == "ok"
        assert CALLS == ["in:ctrl", "route", "out:ctrl"]

    async def test_route_options_replace_the_controller_ones_for_the_same_middleware(
        self, make_app: AppFactory, cache: Cache
    ) -> None:
        CALLS.clear()

        @with_middleware(Tracer, "ctrl")
        @controller("items", cache=cache)
        class Ctrl(Controller):
            @with_middleware(Tracer, "route")
            @get("")
            async def index(self) -> str:
                CALLS.append("route")
                return "ok"

        client = await _client(make_app)
        await client.request("GET", "/items")

        assert CALLS == ["in:route", "route", "out:route"]

    async def test_route_can_remove_a_controller_middleware(self, make_app: AppFactory, cache: Cache) -> None:
        @with_middleware(Blocker)
        @controller("items", cache=cache)
        class Ctrl(Controller):
            @get("open")
            @without_middleware(Blocker)
            async def open_route(self) -> str:
                return "open"

            @get("closed")
            async def closed_route(self) -> str:
                return "closed"

        client = await _client(make_app)

        assert (await client.request("GET", "/items/open")).text == "open"
        assert (await client.request("GET", "/items/closed")).text == "blocked"

    async def test_a_middleware_can_short_circuit_the_route(self, make_app: AppFactory, cache: Cache) -> None:
        @with_middleware(Blocker)
        @controller("items", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> str:
                raise AssertionError("never reached")

        client = await _client(make_app)

        assert (await client.request("GET", "/items")).text == "blocked"

    async def test_a_middleware_error_becomes_a_response(self, make_app: AppFactory, cache: Cache) -> None:
        @with_middleware(Failer)
        @controller("items", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> str:
                return "ok"

        client = await _client(make_app)
        result = await client.request("GET", "/items")

        assert result.status == 403
        assert result.json()["errors"][0]["code"] == "test.blocked"

    async def test_middleware_dependencies_are_injected(self, make_app: AppFactory, cache: Cache) -> None:
        class Counter:
            def __init__(self) -> None:
                self.hits = 0

        class Counting:
            def __init__(self, counter: Counter) -> None:
                self.counter = counter

            def options(self) -> None:
                pass

            async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any:
                self.counter.hits += 1
                return await next()

        @with_middleware(Counting)
        @controller("items", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> str:
                return "ok"

        blnt = await make_app()
        blnt.injector.services.add_singleton(Counter)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())
        await client.request("GET", "/items")

        assert (await blnt.injector.require(Counter)).hits == 1
