from collections.abc import Callable
from typing import Generic, Any

from bolinette import abc, blnt
from bolinette.exceptions import InternalError


class InstantiableAttribute(Generic[abc.inject.T_Instantiable]):
    def __init__(self, _type: type[abc.inject.T_Instantiable], _dict: dict[str, Any]) -> None:
        self._type = _type
        self._dict = _dict

    @property
    def type(self):
        return self._type

    def __getattr__(self, name: str) -> Any:
        if name not in self._dict:
            raise AttributeError(f'Instantiable attribute {self._type} has no {name} member')
        return self._dict[name]

    def pop(self, name: str) -> Any:
        if name not in self._dict:
            raise AttributeError(f'Instantiable attribute {self._type} has no {name} member')
        return self._dict.pop(name)

    def instantiate(self, **kwargs) -> abc.inject.T_Instantiable:
        return self._type(**(self._dict | kwargs))


class BolinetteInjection(abc.inject.Injection):
    def __init__(self, context: abc.Context) -> None:
        super().__init__(context)
        self._collections: dict[str, abc.inject.Collection[Any]] = {}

    def __getattr__(self, name: str) -> abc.inject.Collection[Any]:
        if name not in self._collections:
            raise AttributeError(f'Injection error: no {name} collection registered')
        return self._collections[name]

    def __add_collection__(self, name: str, _type: type[Any]):
        self._collections[name] = InjectionCollection(self.context, name, _type)

    def __get_collection__(self, name: str):
        return self._collections[name]


class InjectionCollection(abc.inject.Collection, Generic[abc.inject.T_Inject]):
    def __init__(self, context: 'blnt.BolinetteContext', name: str, _type: type[abc.inject.T_Inject]) -> None:
        super().__init__(context)
        self._name = name
        self._type = _type
        self._types: dict[str, type[abc.inject.T_Inject]] = {}
        self._instances: dict[str, abc.inject.T_Inject] = {}
        self._functions: dict[str, Callable[[abc.inject.T_Inject], None]] = {}
        self._params: dict[str, dict[str, Any]] = {}

    def __add_instance__(self, name: str, instance: abc.inject.T_Inject) -> None:
        if name not in self._types:
            raise InternalError(f'Injection error: {name} is not a registered type in {self._type} collection')
        if not isinstance(instance, self._types[name]):
            raise InternalError(f'Injection error: object is not of {self._types[name]} type')
        self._instances[name] = instance

    def __add_type__(self, name: str, _type: type[abc.inject.T_Inject], *,
                     func: Callable[[abc.inject.T_Inject], None] | None = None,
                     params: dict[str, Any] = None) -> None:
        if not isinstance(_type, type) or not issubclass(_type, self._type):
            raise InternalError(f'Injection error: {_type} is not a subclass of {self._type}')
        self._types[name] = _type
        if func is not None:
            self._functions[name] = func
        if params is not None:
            self._params[name] = params

    def require(self, name: str, *, immediate: bool = False) -> abc.inject.T_Inject:
        if name not in self._types:
            raise InternalError(f'Injection error: No {name} type found in {self._type} collection')
        if name not in self._instances:
            obj = InjectingObject(self._types[name], name, self,
                                  self._functions.get(name, None), self._params.get(name, None))
            if immediate:
                return obj.instantiate(self.context)
            return obj  # type: ignore
        return self._instances[name]

    def registered(self):
        return (name for name in self._types)


class InjectingObject(Generic[abc.inject.T_Inject]):
    def __init__(self, _type: type[abc.inject.T_Inject], name: str,
                 collection: InjectionCollection[abc.inject.T_Inject],
                 function: Callable[[abc.inject.T_Inject], None] | None,
                 params: dict[str, Any] = None) -> None:
        self._type = _type
        self._name = name
        self._collection = collection
        self._function = function
        self._params = params or {}

    def instantiate(self, context: abc.Context) -> abc.inject.T_Inject:
        instance = self._type(context, **self._params)
        self._collection.__add_instance__(self._name, instance)
        if self._function is not None:
            self._function(instance)
        return instance


class InjectionProxy(Generic[abc.inject.T_Inject]):
    def __init__(self, func: Callable[[Any, abc.inject.Injection], abc.inject.T_Inject]) -> None:
        self._func = func
        self._name = func.__name__

    def __get__(self, instance, _) -> abc.inject.T_Inject:
        if not isinstance(instance, abc.WithContext):
            raise InternalError(f'Injection error: {type(instance)} class must extend bolinette.abc.WithContext')
        context = instance.__blnt_ctx__
        inject = context.inject
        obj = self._func(instance, inject)
        if isinstance(obj, InjectingObject):
            obj = obj.instantiate(context)
        setattr(instance, self._name, obj)
        return obj
