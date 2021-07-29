from typing import TypeVar, Generic

_T = TypeVar('_T')


class InitProxy(Generic[_T]):
    def __init__(self, proxy_cls: type[_T], **kwargs):
        self._proxy_cls = proxy_cls
        self._kwargs = kwargs

    def instantiate(self, **kwargs) -> _T:
        return self._proxy_cls(**(self._kwargs | kwargs))

    def of_type(self, proxy_cls: type[_T]) -> bool:
        return self._proxy_cls == proxy_cls

    def __repr__(self):
        return f'<InitProxy #{self.__hash__()}: {repr(self._proxy_cls)}>'
