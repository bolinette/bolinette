from abc import ABC

from bolinette import abc


class Context(ABC):
    def __init__(self, origin: str):
        self._origin = origin
        self.inject: abc.Injection = None  # type: ignore


class WithContext(ABC):
    def __init__(self, context: Context):
        self.__blnt_ctx__ = context

    @property
    def context(self):
        return self.__blnt_ctx__
