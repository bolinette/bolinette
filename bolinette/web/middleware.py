from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable
from typing import Any

from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bolinette import abc


class Middleware(abc.WithContext):
    __blnt__: 'MiddlewareMetadata' = None

    def __init__(self, context: abc.Context):
        super().__init__(context)
        self.system_priority = 1
        self.options = {}
        self.params = MiddlewareParams()

    def define_options(self) -> dict[str, 'MiddlewareParam']:
        return {}

    async def handle(self, request: Request, params: dict[str, Any],
                     next_func: Callable[[Request, dict[str, Any]], Awaitable[Response]]):
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
    def __init__(self, context: abc.Context):
        super().__init__(context)
        self.system_priority = 0


class MiddlewareParams:
    @staticmethod
    def bool(required=False, default=False):
        return BooleanParam(required, default)

    @staticmethod
    def string(required=False, default=None):
        return StringParam(required, default)

    @staticmethod
    def int(required=False, default=None):
        return IntParam(required, default)

    @staticmethod
    def float(required=False, default=None):
        return FloatParam(required, default)

    @staticmethod
    def list(element: 'MiddlewareParam', required=False, default=None):
        if default is None:
            default = []
        return ListParam(element, required, default)


class MiddlewareParam(ABC):
    def __init__(self, required=False, default=None):
        self.required = required
        self.default = default

    @abstractmethod
    def validate(self, value: str):
        pass


class BooleanParam(MiddlewareParam):
    def validate(self, value: str):
        return True

    def __repr__(self) -> str:
        return 'bool'


class StringParam(MiddlewareParam):
    def validate(self, value: str):
        return value

    def __repr__(self) -> str:
        return 'str'


class IntParam(MiddlewareParam):
    def validate(self, value: str):
        return int(value)

    def __repr__(self) -> str:
        return 'int'


class FloatParam(MiddlewareParam):
    def validate(self, value: str):
        return float(value)

    def __repr__(self) -> str:
        return 'float'


class ListParam(MiddlewareParam):
    def __init__(self, element: MiddlewareParam, required=False, default=None):
        super().__init__(required, default)
        self.element = element

    def validate(self, value: str):
        return [self.element.validate(val) for val in value.split(',')]

    def __repr__(self) -> str:
        return f'list[{repr(self.element)}]'
