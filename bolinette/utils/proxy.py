from typing import Type, TypeVar, Generic

T = TypeVar('T')


class InitProxy(Generic[T]):
    def __init__(self, proxy_cls: Type[T], **kwargs):
        self._proxy_cls = proxy_cls
        self._kwargs = kwargs

    def instantiate(self, **kwargs) -> T:
        return self._proxy_cls(**(self._kwargs | kwargs))

    def of_type(self, proxy_cls: Type[T]) -> bool:
        return self._proxy_cls == proxy_cls

    def __repr__(self):
        return f'<InitProxy #{self.__hash__()}: {repr(self._proxy_cls)}>'
