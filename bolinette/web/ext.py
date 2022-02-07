import inspect
from collections.abc import Callable
from typing import TypeVar

from bolinette.core import BolinetteContext, BolinetteExtension, InstantiableAttribute
from bolinette.data import ext as data_ext
from bolinette.web import (
    WebContext,
    Controller,
    ControllerMetadata,
    ControllerRoute,
    Middleware,
    MiddlewareMetadata,
    HttpMethod,
    Expects,
    Returns,
    Topic,
    TopicMetadata,
    TopicChannel,
)

T_Middleware = TypeVar("T_Middleware", bound=Middleware)
T_Controller = TypeVar("T_Controller", bound=Controller)
T_Topic = TypeVar("T_Topic", bound=Topic)


class WebExtension(BolinetteExtension[WebContext]):
    def __init__(self):
        super().__init__(dependencies=[data_ext])
        self.route = _RouteDecorator()

    def __create_context__(self, context: BolinetteContext) -> WebContext:
        return WebContext(self, context)

    @property
    def __context_type__(self):
        return WebContext

    def controller(
        self,
        controller_name: str,
        path: str | None = None,
        *,
        namespace: str = "/api",
        use_service: bool = True,
        service_name: str = None,
        middlewares: str | list[str] | None = None,
    ):
        _path = path if path is not None else f"/{controller_name}"
        _service_name = service_name if service_name is not None else controller_name
        _middlewares = (
            middlewares
            if isinstance(middlewares, list)
            else [middlewares]
            if isinstance(middlewares, str)
            else []
        )

        def decorator(controller_cls: type[T_Controller]) -> type[T_Controller]:
            controller_cls.__blnt__ = ControllerMetadata(
                controller_name,
                _path,
                use_service,
                _service_name,
                namespace,
                _middlewares,
            )
            self._cache.push(controller_cls, "controller", controller_name)
            return controller_cls

        return decorator

    def middleware(
        self,
        name: str,
        *,
        priority: int = 100,
        auto_load: bool = False,
        loadable: bool = True,
    ):
        def decorator(middleware_cls: type[T_Middleware]) -> type[T_Middleware]:
            middleware_cls.__blnt__ = MiddlewareMetadata(
                name, priority, auto_load, loadable
            )
            self._cache.push(middleware_cls, "middleware", name)
            return middleware_cls

        return decorator

    def topic(self, topic_name: str):
        def decorator(topic_cls: type[T_Topic]) -> type[T_Topic]:
            topic_cls.__blnt__ = TopicMetadata(topic_name)
            self._cache.push(topic_cls, "topic", topic_name)
            return topic_cls

        return decorator

    def channel(self, rule: str):
        def decorator(channel_function: Callable):
            return TopicChannel(channel_function, rule)

        return decorator


class _RouteDecorator:
    def __call__(
        self,
        path: str,
        *,
        method: HttpMethod,
        expects: Expects = None,
        returns: Returns = None,
        middlewares: str | list[str] | None = None,
    ):
        if middlewares is None:
            middlewares = []
        if isinstance(middlewares, str):
            middlewares = [middlewares]

        def decorator(route_function: Callable):
            if not isinstance(
                route_function, InstantiableAttribute
            ) and not inspect.iscoroutinefunction(route_function):
                raise ValueError(
                    f'Route "{route_function.__name__}" must be an async function'
                )
            if expects is not None and not isinstance(expects, Expects):
                raise ValueError(
                    f'Route "{route_function.__name__}": expects argument must be of type web.Expects'
                )
            if returns is not None and not isinstance(returns, Returns):
                raise ValueError(
                    f'Route "{route_function.__name__}": expects argument must be of type web.Returns'
                )
            inner_route = None
            if isinstance(route_function, InstantiableAttribute):
                inner_route = route_function
            docstring = route_function.__doc__
            return InstantiableAttribute(
                ControllerRoute,
                dict(
                    func=route_function,
                    path=path,
                    method=method,
                    docstring=docstring,
                    expects=expects,
                    returns=returns,
                    inner_route=inner_route,
                    middlewares=middlewares,
                ),
            )

        return decorator

    def get(
        self,
        path: str,
        *,
        returns: Returns = None,
        middlewares: str | list[str] | None = None,
    ):
        return self(
            path,
            method=HttpMethod.GET,
            expects=None,
            returns=returns,
            middlewares=middlewares,
        )

    def post(
        self,
        path: str,
        *,
        expects: Expects = None,
        returns: Returns = None,
        middlewares: str | list[str] | None = None,
    ):
        return self(
            path,
            method=HttpMethod.POST,
            expects=expects,
            returns=returns,
            middlewares=middlewares,
        )

    def put(
        self,
        path: str,
        *,
        expects: Expects = None,
        returns: Returns = None,
        middlewares: str | list[str] | None = None,
    ):
        return self(
            path,
            method=HttpMethod.PUT,
            expects=expects,
            returns=returns,
            middlewares=middlewares,
        )

    def patch(
        self,
        path: str,
        *,
        expects: Expects = None,
        returns: Returns = None,
        middlewares: str | list[str] | None = None,
    ):
        return self(
            path,
            method=HttpMethod.PATCH,
            expects=expects,
            returns=returns,
            middlewares=middlewares,
        )

    def delete(
        self,
        path: str,
        *,
        returns: Returns = None,
        middlewares: str | list[str] | None = None,
    ):
        return self(
            path,
            method=HttpMethod.DELETE,
            expects=None,
            returns=returns,
            middlewares=middlewares,
        )


ext = WebExtension()
