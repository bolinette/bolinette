from collections.abc import Callable
from typing import Generic, TypeVar, Any

from bolinette import abc, blnt
from bolinette.exceptions import InternalError

_T1 = TypeVar('_T1')


class InstantiableAttribute(Generic[_T1]):
    def __init__(self, _type: type[_T1], _dict: dict[str, Any]) -> None:
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

    def instantiate(self, **kwargs) -> _T1:
        return self._type(**(self._dict | kwargs))


_T = TypeVar('_T', bound=abc.WithContext)


class BolinetteInjection(abc.WithContext, Generic[_T]):
    """
    Hold collections of instance injection
    """
    def __init__(self, context: 'blnt.BolinetteContext') -> None:
        super().__init__(context)
        self._collections: dict[str, InjectionCollection[_T]] = {}

    def __getattr__(self, name: str) -> 'InjectionCollection[_T]':
        if name not in self._collections:
            raise AttributeError(f'Injection error: no {name} collection registered')
        return self._collections[name]

    def __add_collection__(self, name: str, _type: type[_T]):
        self._collections[name] = InjectionCollection(self.context, name, _type)

    def __get_collection__(self, name: str) -> 'InjectionCollection[_T]':
        return self._collections[name]


class InjectionCollection(abc.WithContext, Generic[_T]):
    """
    Holds a collection of instances to inject at runtime
    """
    def __init__(self, context: 'blnt.BolinetteContext', name: str, _type: type[_T]) -> None:
        super().__init__(context)
        self._name = name
        self._type = _type
        self._types: dict[str, type[_T]] = {}
        self._instances: dict[str, _T] = {}
        self._functions: dict[str, Callable[[_T], None]] = {}
        self._params: dict[str, dict[str, Any]] = {}

    def __add_instance__(self, name: str, instance: _T) -> None:
        """
        Add an instance to the collection
        """
        if name not in self._types:
            raise InternalError(f'Injection error: {name} is not a registered type in {self._type} collection')
        if not isinstance(instance, self._types[name]):
            raise InternalError(f'Injection error: object is not of {self._types[name]} type')
        self._instances[name] = instance

    def __add_type__(self, name: str, _type: type[_T], *,
                     func: Callable[[_T], None] | None = None,
                     params: dict[str, Any] = None) -> None:
        """
        Add an type that can be instantiated
        """
        if not isinstance(_type, type) or not issubclass(_type, self._type):
            raise InternalError(f'Injection error: {_type} is not a subclass of {self._type}')
        self._types[name] = _type
        if func is not None:
            self._functions[name] = func
        if params is not None:
            self._params[name] = params

    def require(self, name: str, *, immediate: bool = False) -> _T:
        """
        Gets an instance from the injection collection
        """
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
        """
        Gets all names registered inside the collection
        """
        return (name for name in self._types)


class InjectingObject(Generic[_T]):
    """
    Hold injection information before the first call when the instantiation actually happens
    """
    def __init__(self, _type: type[_T], name: str,
                 collection: InjectionCollection[_T],
                 function: Callable[[_T], None] | None,
                 params: dict[str, Any] = None) -> None:
        self._type = _type
        self._name = name
        self._collection = collection
        self._function = function
        self._params = params or {}

    def instantiate(self, context: abc.Context) -> _T:
        """
        Gets the type from the collection and instantiates it
        """
        instance = self._type(context, **self._params)
        self._collection.__add_instance__(self._name, instance)
        if self._function is not None:
            self._function(instance)
        return instance


class InjectionProxy(Generic[_T]):
    """
    Is called for the first time and replaced by the object inside the caller instance
    """
    def __init__(self, func: Callable[[Any, abc.Injection], _T]) -> None:
        self._func = func
        self._name = func.__name__

    def __get__(self, instance, _) -> _T:
        if not isinstance(instance, abc.WithContext):
            raise InternalError(f'Injection error: {type(instance)} class must extend bolinette.abc.WithContext')
        context = instance.__blnt_ctx__
        inject = context.inject
        obj = self._func(instance, inject)
        if isinstance(obj, InjectingObject):
            obj = obj.instantiate(context)
        setattr(instance, self._name, obj)
        return obj
