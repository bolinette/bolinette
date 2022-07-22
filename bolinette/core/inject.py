import inspect
from collections.abc import Callable
from typing import Any, Generic, ParamSpec, TypeVar

from bolinette.core import Cache, InjectionStrategy
from bolinette.core.cache import RegisteredType
from bolinette.core.exceptions import (
    AnnotationMissingInjectionError,
    InstanceExistsInjectionError,
    InstanceNotExistInjectionError,
    InvalidArgCountInjectionError,
    NoLiteralMatchInjectionError,
    NoPositionalParameterInjectionError,
    TooManyLiteralMatchInjectionError,
    TypeNotRegisteredInjectionError,
    TypeRegisteredInjectionError,
)

P_Func = ParamSpec("P_Func")
T_Func = TypeVar("T_Func")
T_Instance = TypeVar("T_Instance")


class InjectionContext:
    def __init__(self) -> None:
        self._instances: dict[type[Any], Any] = {}

    def __contains__(self, cls: Any) -> bool:
        if not isinstance(cls, type):
            raise TypeError('Only types allowed')
        return cls in self._instances

    def __setitem__(self, cls: type[T_Instance], instance: T_Instance) -> None:
        if cls in self:
            raise InstanceExistsInjectionError(cls)
        if not isinstance(instance, cls):
            raise TypeError('Object is not an instance of cls')
        self._instances[cls] = instance

    def __getitem__(self, cls: type[T_Instance]) -> T_Instance:
        if cls not in self:
            raise InstanceNotExistInjectionError(cls)
        return self._instances[cls]


class Injection:
    def __init__(self, cache: Cache, global_ctx: InjectionContext) -> None:
        self._cache = cache
        self._global_ctx = global_ctx
        self.add(Injection, self)

    def _has_instance(self, cls: type[Any]) -> bool:
        return cls in self._global_ctx

    def _get_instance(self, cls: type[T_Instance]) -> T_Instance:
        return self._global_ctx[cls]

    def _set_instance(self, cls: type[T_Instance], instance: T_Instance) -> None:
        self._global_ctx[cls] = instance

    def _find_type_by_name(
        self, func: Callable, param: str, name: str
    ) -> type[Any] | None:
        names = self._cache.find_types_by_name(name)
        if not names:
            raise NoLiteralMatchInjectionError(func, param, name)
        if (l := len(names)) > 1:
            raise TooManyLiteralMatchInjectionError(func, param, name, l)
        return names[0]

    def _resolve_args(
        self,
        func: Callable[P_Func, T_Func],
        immediate: bool,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        params = dict(inspect.signature(func).parameters)
        if any(
            (n, p)
            for n, p in params.items()
            if p.kind in [p.POSITIONAL_ONLY, p.VAR_POSITIONAL]
        ):
            raise NoPositionalParameterInjectionError(func)

        f_args: dict[str, Any] = {}
        _args = [*args]
        _kwargs = {**kwargs}

        # Iterating over the parameters of the callable
        for p_name, param in params.items():
            if param.kind == param.VAR_KEYWORD:
                for kw_name, kw_value in _kwargs.items():
                    f_args[kw_name] = kw_value
                _kwargs = {}
                break

            # Looking for parameters in the args and kwargs
            if _args:
                f_args[p_name] = _args.pop(0)
            elif p_name in _kwargs:
                f_args[p_name] = _kwargs.pop(p_name)
            elif param.default is not param.empty:
                f_args[p_name] = param.default
            else:
                # No params were found in the kwargs, try to find them in the registry
                hint = param.annotation
                if hint == inspect.Signature.empty:
                    raise AnnotationMissingInjectionError(func, p_name)
                elif isinstance(hint, type) or isinstance(hint, str):
                    cls: type[Any] | None = None
                    if isinstance(hint, str):
                        cls = self._find_type_by_name(func, p_name, hint)
                    else:
                        cls = hint
                    if cls is not None:
                        if not self._cache.has_type(cls):
                            raise TypeNotRegisteredInjectionError(cls)
                        else:
                            if self._has_instance(cls):
                                f_args[p_name] = self._get_instance(cls)
                            else:
                                if immediate:
                                    f_args[p_name] = self._instanciate(cls)
                                else:
                                    f_args[p_name] = _ProxyHook(cls)

        if _args or _kwargs:
            raise InvalidArgCountInjectionError(
                func, len(params), len(args) + len(kwargs)
            )

        return f_args

    def _hook_proxies(self, instance: Any) -> None:
        cls = type(instance)
        attrs = dict(vars(instance))
        for name, attr in attrs.items():
            if isinstance(attr, _ProxyHook):
                delattr(instance, name)
                setattr(cls, name, _InjectionProxy(self, name, attr.cls))

    def _instanciate(
        self,
        cls: type[T_Instance],
        *,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> T_Instance:
        if self._has_instance(cls):
            raise InstanceExistsInjectionError(cls)
        r_type = self._cache.get_type(cls)
        func_args = self._resolve_args(cls, False, args or [], (kwargs or {}) | (r_type.params or {}))
        instance = cls(**func_args)
        if (r_type.func is not None):
            self.call(r_type.func, args=[instance])
        self._hook_proxies(instance)
        self._set_instance(cls, instance)
        return instance

    def call(
        self,
        func: Callable[P_Func, T_Func],
        *,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> T_Func:
        func_args = self._resolve_args(func, True, args or [], kwargs or {})
        return func(**func_args)

    def add(
        self,
        cls: type[T_Instance],
        strategy: InjectionStrategy,
        func: Callable[[T_Instance], None] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        if self._cache.has_type(cls):
            raise TypeRegisteredInjectionError(cls)
        self._cache.add_type(cls, strategy, func, params)

    def require(self, cls: type[T_Instance]) -> T_Instance:
        if not self._cache.has_type(cls):
            raise TypeNotRegisteredInjectionError(cls)
        if self._has_instance(cls):
            return self._get_instance(cls)
        return self._instanciate(cls)


class _ProxyHook:
    def __init__(self, cls: type[Any]) -> None:
        self.cls = cls


class _InjectionProxy(Generic[T_Instance]):
    def __init__(
        self, inject: Injection, name: str, cls: type[T_Instance]
    ) -> None:
        self._inject = inject
        self._name = name
        self._cls = cls

    def __get__(self, instance: Any, _) -> T_Instance:
        obj = None
        if self._inject._has_instance(self._cls):
            obj = self._inject._get_instance(self._cls)
        else:
            obj = self._inject._instanciate(self._cls)
        setattr(instance, self._name, obj)
        return obj
