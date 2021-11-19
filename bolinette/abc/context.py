from abc import ABC
from typing import Any

from bolinette import abc


class Context(ABC):
    def __init__(self, origin: str, *, inject: 'abc.inject.Injection'):
        self._ctx: dict[str, Any] = {}
        self._origin = origin
        self.inject = inject

    def __getitem__(self, key: str):
        if key not in self._ctx:
            raise KeyError(f'No {key} element registered in context')
        return self._ctx[key]

    def __setitem__(self, key: str, value: Any):
        self._ctx[key] = value

    def __delitem__(self, key: str):
        if key not in self._ctx:
            raise KeyError(f'No {key} element registered in context')
        del self._ctx[key]

    def __contains__(self, key: str):
        return key in self._ctx


class WithContext(ABC):
    def __init__(self, context: Context, **kwargs):
        self.__blnt_ctx__ = context

    @property
    def context(self):
        return self.__blnt_ctx__
