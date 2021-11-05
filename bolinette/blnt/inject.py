import collections
from collections.abc import Callable
from typing import Generic, Any

from bolinette import abc, blnt
from bolinette.abc.inject.injection import T_Inject
from bolinette.exceptions import InternalError


class InstantiableAttribute(Generic[abc.inject.T_Instantiable]):
    def __init__(self, _type: type[abc.inject.T_Instantiable], _dict: dict[str, Any]) -> None:
        self._type = _type
        self._dict = _dict

    @property
    def type(self):
        return self._type

    def pop(self, name: str) -> Any:
        if name not in self._dict:
            raise AttributeError(f'Instantiable attribute {self._type} has no {name} member')
        return self._dict.pop(name)

    def instantiate(self, **kwargs) -> abc.inject.T_Instantiable:
        return self._type(**(self._dict | kwargs))


class RegisteredType(Generic[abc.inject.T_Inject]):
    def __init__(self, _type: type[abc.inject.T_Inject], collection: str, name: str,
                 func: Callable[[abc.inject.T_Inject], None] | None = None,
                 params: dict[str, Any] = None) -> None:
        self.type = _type
        self.collection = collection
        self.name = name
        self.instance: abc.inject.T_Inject | None = None
        self.func = func
        self.params = params


class BolinetteInjection(abc.inject.Injection):
    def __init__(self, context: abc.Context) -> None:
        super().__init__(context)
        self._collections: dict[str, abc.inject.Collection[Any]] = {}
        self._by_type: dict[type, RegisteredType[Any]] = {}
        self._by_collection: dict[str, dict[str, RegisteredType[Any]]] = {}

    def register(self, _type: type[abc.inject.T_Inject], collection: str, name: str, *,
                 func: Callable[[abc.inject.T_Inject], None] | None = None,
                 params: dict[str, Any] = None) -> None:
        registered = RegisteredType(_type, collection, name, func, params)
        self._by_type[_type] = registered
        if collection not in self._by_collection:
            self._by_collection[collection] = {}
        self._by_collection[collection][name] = registered

    def _require_by_type(self, _type: type[abc.inject.T_Inject]) -> RegisteredType[abc.inject.T_Inject]:
        if _type not in self._by_type:
            raise InternalError(f'Injection error: No {_type} type found in injection registry')
        return self._by_type[_type]

    def _require_by_names(self, collection: str, name: str) -> RegisteredType[Any]:
        if collection in self._by_collection and name in self._by_collection[collection]:
            return self._by_collection[collection][name]
        raise InternalError(f'Injection error: No {collection}.{name} type found in injection registry')

    def require(self, *args, **kwargs) -> Any:
        def _get_wrapper():
            match args:
                case [_type]:
                    return self._require_by_type(_type)
                case [_collection, _name]:
                    return self._require_by_names(_collection, _name)
            raise AssertionError(f'Argument mismatch')

        wrapper = _get_wrapper()
        if wrapper.instance is None:
            obj = InjectingObject(wrapper.type, wrapper, wrapper.func, wrapper.params)
            if kwargs.get('immediate', False):
                return obj.instantiate(self.context)
            return obj
        return wrapper.instance

    def registered(self, *args, **kwargs):
        if (of_type := kwargs.get('of_type', None)) is not None:
            if not isinstance(of_type, type):
                raise ValueError(f'of_type argument must be a type class')
            for _type in self._by_type:
                if issubclass(_type, of_type):
                    yield _type
        elif kwargs.get('get_strings', False):
            for collection in self._by_collection:
                for name in self._by_collection[collection]:
                    yield collection, name
        else:
            for _type in self._by_type:
                yield _type


class InjectingObject(Generic[abc.inject.T_Inject]):
    def __init__(self, _type: type[abc.inject.T_Inject],
                 wrapper: RegisteredType,
                 function: Callable[[abc.inject.T_Inject], None] | None,
                 params: dict[str, Any] = None) -> None:
        self._type = _type
        self._wrapper = wrapper
        self._function = function
        self._params = params or {}

    def instantiate(self, context: abc.Context) -> abc.inject.T_Inject:
        instance = self._type(context, **self._params)
        self._wrapper.instance = instance
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
