from typing import Any, Dict, Callable, Awaitable

from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bolinette import blnt


class Middleware:
    __blnt__: 'MiddlewareMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        self.system_priority = 1
        self.context = context
        self.options = {}

    async def handle(self, request: Request, params: Dict[str, Any],
                     next_func: Callable[[Request, Dict[str, Any]], Awaitable[Response]]):
        return await next_func(request, params)

    def __repr__(self):
        return f'<Middleware {self.__blnt__.name}>'


class MiddlewareMetadata:
    def __init__(self, name: str, priority: int, auto_load: bool, loadable: bool):
        self.name = name
        self.priority = priority
        self.auto_load = auto_load
        self.loadable = loadable


class InternalMiddleware(Middleware):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self.system_priority = 0
