from abc import ABC

from bolinette import abc


class Context(ABC):
    def __init__(self, origin: str, *, inject: 'abc.inject.Injection'):
        self._origin = origin
        self.inject: abc.inject.Injection = inject


class WithContext(ABC):
    def __init__(self, context: Context, **kwargs):
        self.__blnt_ctx__ = context

    @property
    def context(self):
        return self.__blnt_ctx__
