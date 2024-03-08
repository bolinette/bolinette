from collections.abc import Awaitable, Callable

from aiohttp import web

from bolinette.core import meta
from bolinette.core.types import Type
from bolinette.web import with_middleware, without_middleware
from bolinette.web.middleware import MiddlewareBag


def test_add_middleware() -> None:
    class TestMiddleware:
        def options(self) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    @with_middleware(TestMiddleware)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    mdlw_t = Type(TestMiddleware)
    assert mdlw_t in bag.added
    mdlw_meta = bag.added[mdlw_t]
    assert mdlw_meta.args == ()
    assert mdlw_meta.kwargs == {}


def test_add_middleware_on_class() -> None:
    class TestMiddleware:
        def options(self) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    @with_middleware(TestMiddleware)
    class TestCtrl:
        pass

    assert meta.has(TestCtrl, MiddlewareBag)
    bag = meta.get(TestCtrl, MiddlewareBag)
    mdlw_t = Type(TestMiddleware)
    assert mdlw_t in bag.added
    mdlw_meta = bag.added[mdlw_t]
    assert mdlw_meta.args == ()
    assert mdlw_meta.kwargs == {}


def test_add_middleware_with_options() -> None:
    class TestMiddleware:
        def options(self, value: int) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    @with_middleware(TestMiddleware, value=1)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    mdlw_t = Type(TestMiddleware)
    assert mdlw_t in bag.added
    mdlw_meta = bag.added[mdlw_t]
    assert mdlw_meta.args == ()
    assert mdlw_meta.kwargs == {"value": 1}


def test_add_middleware_with_default_options() -> None:
    class TestMiddleware:
        def options(self, value: int = 0) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    @with_middleware(TestMiddleware)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    mdlw_t = Type(TestMiddleware)
    assert mdlw_t in bag.added
    mdlw_meta = bag.added[mdlw_t]
    assert mdlw_meta.args == ()
    assert mdlw_meta.kwargs == {}


def test_add_two_middlewares() -> None:
    class TestMiddleware1:
        def options(self) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    class TestMiddleware2:
        def options(self, value: int) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    @with_middleware(TestMiddleware1)
    @with_middleware(TestMiddleware2, 42)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    mdlw1_t = Type(TestMiddleware1)
    assert mdlw1_t in bag.added
    mdlw1_meta = bag.added[mdlw1_t]
    assert mdlw1_meta.args == ()
    assert mdlw1_meta.kwargs == {}
    mdlw2_t = Type(TestMiddleware2)
    assert mdlw2_t in bag.added
    mdlw2_meta = bag.added[mdlw2_t]
    assert mdlw2_meta.args == (42,)
    assert mdlw2_meta.kwargs == {}


def test_remove_middleware() -> None:
    class TestMiddleware:
        def options(self) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    @without_middleware(TestMiddleware)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    mdlw_t = Type(TestMiddleware)
    assert mdlw_t in bag.removed


def test_remove_two_middlewares() -> None:
    class TestMiddleware1:
        def options(self) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    class TestMiddleware2:
        def options(self) -> None: ...

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response: ...

    @without_middleware(TestMiddleware1)
    @without_middleware(TestMiddleware2)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    mdlw1_t = Type(TestMiddleware1)
    assert mdlw1_t in bag.removed
    mdlw2_t = Type(TestMiddleware2)
    assert mdlw2_t in bag.removed
