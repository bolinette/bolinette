import inspect
from collections.abc import Callable
from typing import Generic, Any

from bolinette import abc
from bolinette.exceptions import InternalError


def _resolve_dependencies(context: abc.Context, _type: type[abc.inject.T_Inject]):
    args = {}
    errors = []
    if not hasattr(_type, '__blnt_inject__'):
        params = inspect.signature(_type).parameters
        injected = {}
        for p_name, param in params.items():
            if p_name == 'context':
                injected[p_name] = '__blnt_ctx__'
                continue
            hint = param.annotation
            if hint == inspect._empty:
                errors.append(f'Injection error: {p_name} param in {_type}.__init__ requires an annotation')
            elif isinstance(hint, type) or isinstance(hint, str):
                injected[p_name] = hint
        setattr(_type, '__blnt_inject__', injected)
    injected: dict = getattr(_type, '__blnt_inject__')
    for p_name, hook in injected.items():
        if hook == '__blnt_ctx__':
            args[p_name] = context
        else:
            args[p_name] = _ProxyHook(p_name)
    if len(errors) > 0:
        raise InternalError(f'Injection errors raised while instantiating {_type}:\n  ' + '\n  '.join(errors))
    return args


def _hook_proxies(instance: Any):
    def _call_require(_hint):
        return lambda _, inject: inject.require(_hint)
    _type = type(instance)
    injected = getattr(_type, '__blnt_inject__')
    for name, hook in [(n, v) for n, v in vars(instance).items() if isinstance(v, _ProxyHook)]:
        delattr(instance, name)
        if not hasattr(_type, name):
            setattr(_type, name, InjectionProxy(_call_require(injected[hook.name]), name))


def instantiate_type(context: abc.Context, _type: type[abc.inject.T_Inject]) -> abc.inject.T_Inject:
    args = _resolve_dependencies(context, _type)
    instance = _type(**args)
    _hook_proxies(instance)
    return instance


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
        self._by_name: dict[str, RegisteredType[Any]] = {}

    def register(self, _type: type[abc.inject.T_Inject], collection: str, name: str, *,
                 func: Callable[[abc.inject.T_Inject], None] | None = None,
                 params: dict[str, Any] = None) -> None:
        registered = RegisteredType(_type, collection, name, func, params)
        self._by_type[_type] = registered
        if collection not in self._by_collection:
            self._by_collection[collection] = {}
        self._by_collection[collection][name] = registered
        self._by_name[f'{_type.__module__}.{_type.__name__}'] = registered

    def _require_by_type(self, _type: type[abc.inject.T_Inject]) -> RegisteredType[abc.inject.T_Inject]:
        if _type not in self._by_type:
            raise InternalError(f'Injection error: No {_type} type found in injection registry')
        return self._by_type[_type]

    def _require_by_collection(self, collection: str, name: str) -> RegisteredType[Any]:
        if collection in self._by_collection and name in self._by_collection[collection]:
            return self._by_collection[collection][name]
        raise InternalError(f'Injection error: No {collection}.{name} type found in injection registry')

    def _require_by_name(self, name: str):
        if name in self._by_name:
            return self._by_name[name]
        match [n for n in self._by_name if name in n]:
            case matches if len(matches) > 1:
                raise InternalError(f'Injection error: {len(matches)} matches found for {name} in injection registry')
            case matches if len(matches) > 0:
                return self._by_name[matches[0]]
        raise InternalError(f'Injection error: No match for {name} found in injection registry')

    def require(self, *args, **kwargs) -> Any:
        def _get_wrapper():
            match args:
                case [_type] if isinstance(_type, type):
                    return self._require_by_type(_type)
                case [_name] if isinstance(_name, str):
                    return self._require_by_name(_name)
                case [_collection, _name] if isinstance(_collection, str) and isinstance(_name, str):
                    return self._require_by_collection(_collection, _name)
            raise AssertionError(f'Argument mismatch')

        wrapper = _get_wrapper()
        if wrapper.instance is None:
            obj = InjectingObject(self.context, wrapper)
            if kwargs.get('immediate', False):
                return obj.instantiate()
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


class InjectingObject(abc.WithContext, Generic[abc.inject.T_Inject]):
    def __init__(self, context: abc.Context, wrapper: RegisteredType) -> None:
        super().__init__(context)
        self._type = wrapper.type
        self._wrapper = wrapper
        self._function = wrapper.func
        self._params = wrapper.params or {}

    def instantiate(self) -> abc.inject.T_Inject:
        instance = instantiate_type(self.context, self._type)
        self._wrapper.instance = instance
        if self._function is not None:
            self._function(instance)
        return instance


class InjectionProxy(Generic[abc.inject.T_Inject]):
    def __init__(self, func: Callable[[Any, abc.inject.Injection], abc.inject.T_Inject], name: str) -> None:
        self._func = func
        self._name = name

    def __get__(self, instance, _) -> abc.inject.T_Inject:
        if instance is None:
            return None
        if not isinstance(instance, abc.WithContext):
            raise InternalError(f'Injection error: {type(instance)} class must extend bolinette.abc.WithContext')
        context = instance.__blnt_ctx__
        inject = context.inject
        obj = self._func(instance, inject)
        if isinstance(obj, InjectingObject):
            obj = obj.instantiate()
        setattr(instance, self._name, obj)
        return obj

    def __repr__(self) -> str:
        return f'<InjectionProxy {self._name}>'


class _ProxyHook:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self):
        return self._name

    def __repr__(self) -> str:
        return f'<ProxyHook {self._name}>'

    def __getattr__(self, _):
        raise InternalError('Injected instance has not been resolved yet.\n'
                            '  Do not access injected instances inside __init__().\n'
                            '  Use init function to process any startup logic.')
