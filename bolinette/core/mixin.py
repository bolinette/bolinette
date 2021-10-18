from collections.abc import Iterator, Callable

from bolinette import blnt, types


class Mixin:
    def __init__(self):
        self.__props__ = MixinProps(self)
        self._methods = {}
        for method_name, method in self.__props__.get_service_methods():
            self._methods[method_name] = method

    def __contains__(self, key):
        return key in self._methods

    def __getitem__(self, key):
        return self._methods[key]

    def columns(self) -> dict[str, 'blnt.InstantiableAttribute']:
        pass

    def relationships(self) -> dict[str, 'types.defs.Relationship']:
        pass

    def payload(self, model):
        pass

    def response(self, model):
        pass


class MixinProps(blnt.Properties):
    def get_service_methods(self) -> Iterator[tuple[str, 'MixinServiceMethod']]:
        return self._get_cls_attributes_of_type(type(self.parent), MixinServiceMethod)


class MixinServiceMethod:
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func
