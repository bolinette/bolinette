from abc import ABC, abstractmethod
from enum import auto, unique, Enum
from typing import Any

from aiohttp import web as aio_web
from aiohttp.web_request import Request

from bolinette import abc


@unique
class HttpMethod(Enum):
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()

    @property
    def http_verb(self):
        return self.name


class Controller(abc.inject.Injectable, abc.WithContext, ABC):
    def __init__(self, context: abc.Context) -> None:
        abc.WithContext.__init__(self, context)


class Route(ABC):
    def __init__(self, controller: Controller, method: HttpMethod) -> None:
        self.controller = controller
        self.method = method

    @abstractmethod
    async def call_middleware_chain(self, request: Request, params: dict[str, Any]): ...


class Resources(ABC):
    def init_web(self, app: aio_web.Application): ...

    def add_route(self, path: str, route: Route): ...
