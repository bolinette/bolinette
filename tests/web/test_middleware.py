from bolinette import meta
from bolinette.ext.web import with_middleware, without_middleware
from bolinette.ext.web.middleware import MiddlewareBag


def test_add_middleware() -> None:
    class TestMiddleware:
        def handle(self) -> None:
            pass

    @with_middleware(TestMiddleware)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    assert TestMiddleware in bag.added
    mdlw_meta = bag.added[TestMiddleware]
    assert mdlw_meta.args == ()
    assert mdlw_meta.kwargs == {}


def test_add_middleware_with_options() -> None:
    class TestMiddleware:
        def __init__(self, value: int) -> None:
            pass

        def handle(self) -> None:
            pass

    @with_middleware(TestMiddleware, value=1)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    assert TestMiddleware in bag.added
    mdlw_meta = bag.added[TestMiddleware]
    assert mdlw_meta.args == ()
    assert mdlw_meta.kwargs == {"value": 1}


def test_add_middleware_with_default_options() -> None:
    class TestMiddleware:
        def __init__(self, value: int = 0) -> None:
            pass

        def handle(self) -> None:
            pass

    @with_middleware(TestMiddleware)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    assert TestMiddleware in bag.added
    mdlw_meta = bag.added[TestMiddleware]
    assert mdlw_meta.args == ()
    assert mdlw_meta.kwargs == {}


def test_add_two_middlewares() -> None:
    class TestMiddleware1:
        def handle(self) -> None:
            pass

    class TestMiddleware2:
        def __init__(self, value: int) -> None:
            pass

        def handle(self) -> None:
            pass

    @with_middleware(TestMiddleware1)
    @with_middleware(TestMiddleware2, 42)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    assert TestMiddleware1 in bag.added
    mdlw1_meta = bag.added[TestMiddleware1]
    assert mdlw1_meta.args == ()
    assert mdlw1_meta.kwargs == {}
    assert TestMiddleware2 in bag.added
    mdlw2_meta = bag.added[TestMiddleware2]
    assert mdlw2_meta.args == (42,)
    assert mdlw2_meta.kwargs == {}


def test_remove_middleware() -> None:
    class TestMiddleware:
        def handle(self) -> None:
            pass

    @without_middleware(TestMiddleware)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    assert TestMiddleware in bag.removed


def test_remove_two_middlewares() -> None:
    class TestMiddleware1:
        def handle(self) -> None:
            pass

    class TestMiddleware2:
        def handle(self) -> None:
            pass

    @without_middleware(TestMiddleware1)
    @without_middleware(TestMiddleware2)
    def test_route() -> None:
        pass

    assert meta.has(test_route, MiddlewareBag)
    bag = meta.get(test_route, MiddlewareBag)
    assert TestMiddleware1 in bag.removed
    assert TestMiddleware2 in bag.removed
