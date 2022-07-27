import inspect
from collections.abc import Callable
from typing import Any, Generic, ParamSpec, TypeVar

from bolinette.core import Cache, InjectionStrategy, meta
from bolinette.core.cache import RegisteredType
from bolinette.core.exceptions import (
    AnnotationMissingInjectionError,
    InjectionError,
    InstanceExistsInjectionError,
    InstanceNotExistInjectionError,
    InvalidArgCountInjectionError,
    NoLiteralMatchInjectionError,
    NoPositionalParameterInjectionError,
    NoScopedContextInjectionError,
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
            raise TypeError("Only types allowed")
        return cls in self._instances

    def __setitem__(self, cls: type[T_Instance], instance: T_Instance) -> None:
        if cls in self:
            raise InstanceExistsInjectionError(cls)
        if not isinstance(instance, cls):
            raise TypeError("Object is not an instance of cls")
        self._instances[cls] = instance

    def __getitem__(self, cls: type[T_Instance]) -> T_Instance:
        if cls not in self:
            raise InstanceNotExistInjectionError(cls)
        return self._instances[cls]


class Injection:
    def __init__(self, cache: Cache, global_ctx: InjectionContext) -> None:
        self._cache = cache
        self._global_ctx = global_ctx
        self._add_safe(Cache, InjectionStrategy.Singleton, self._cache)
        self._add_safe(Injection, InjectionStrategy.Singleton, self)

    def _add_safe(
        self, cls: type[T_Instance], strategy: InjectionStrategy, instance: T_Instance
    ):
        if not self._cache.has_type(cls):
            self.add(cls, strategy)
        if cls not in self._global_ctx:
            self._global_ctx[cls] = instance

    def _has_instance(self, r_type: RegisteredType[Any]) -> bool:
        if r_type.strategy is InjectionStrategy.Scoped:
            raise NoScopedContextInjectionError(r_type.cls)
        return (
            r_type.strategy is InjectionStrategy.Singleton
            and r_type.cls in self._global_ctx
        )

    def _get_instance(self, r_type: RegisteredType[T_Instance]) -> T_Instance:
        return self._global_ctx[r_type.cls]

    def _set_instance(
        self, r_type: RegisteredType[T_Instance], instance: T_Instance
    ) -> None:
        if r_type.strategy is InjectionStrategy.Singleton:
            self._global_ctx[r_type.cls] = instance

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
                            r_type = self._cache.get_type(cls)
                            if self._has_instance(r_type):
                                f_args[p_name] = self._get_instance(r_type)
                            else:
                                if immediate:
                                    f_args[p_name] = self._instanciate(r_type)
                                else:
                                    f_args[p_name] = _ProxyHook(r_type)

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
                setattr(cls, name, _InjectionProxy(name, attr.r_type))

    def _instanciate(
        self,
        r_type: RegisteredType[T_Instance],
        *,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> T_Instance:
        if self._has_instance(r_type):
            raise InstanceExistsInjectionError(r_type.cls)
        func_args = self._resolve_args(
            r_type.cls, False, args or [], (kwargs or {}) | (r_type.params or {})
        )
        instance = r_type.cls(**func_args)
        meta.set(instance, Injection, self)
        if r_type.func is not None:
            self.call(r_type.func, args=[instance])
        self._hook_proxies(instance)
        self._set_instance(r_type, instance)
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
        instance: None | T_Instance = None,
    ) -> None:
        if self._cache.has_type(cls):
            raise TypeRegisteredInjectionError(cls)
        r_type = self._cache.add_type(cls, strategy, func, params)
        if instance is not None:
            if not isinstance(instance, cls):
                raise InjectionError(f"Object provided must an instance of type {cls}")
            if strategy is not InjectionStrategy.Singleton:
                raise InjectionError(
                    f"Type {cls} must be a singleton if an instance is provided"
                )
            self._set_instance(r_type, instance)

    def require(self, cls: type[T_Instance]) -> T_Instance:
        if not self._cache.has_type(cls):
            raise TypeNotRegisteredInjectionError(cls)
        r_type = self._cache.get_type(cls)
        if self._has_instance(r_type):
            return self._get_instance(r_type)
        return self._instanciate(r_type)

    def get_scoped_session(self) -> "_ScopedInjection":
        return _ScopedInjection(self, self._cache, self._global_ctx, InjectionContext())


class _ProxyHook:
    def __init__(self, r_type: RegisteredType[Any]) -> None:
        self.r_type = r_type


class _InjectionProxy(Generic[T_Instance]):
    def __init__(self, name: str, r_type: RegisteredType[T_Instance]) -> None:
        self._name = name
        self._r_type = r_type

    def __get__(self, instance: Any, _) -> T_Instance:
        if not meta.has(instance, Injection):
            raise InjectionError(
                f"Type {self._r_type.cls} has not been intanciated through the injection system"
            )
        inject = meta.get(instance, Injection)
        obj: T_Instance
        if inject._has_instance(self._r_type):
            obj = inject._get_instance(self._r_type)
        else:
            obj = inject._instanciate(self._r_type)
        setattr(instance, self._name, obj)
        return obj


class _ScopedInjection(Injection):
    def __init__(
        self,
        global_inject: Injection,
        cache: Cache,
        global_ctx: InjectionContext,
        scoped_ctx: InjectionContext,
    ) -> None:
        super().__init__(cache, global_ctx)
        self._global_inject = global_inject
        self._scoped_ctx = scoped_ctx
        self._scoped_ctx[Injection] = self

    def _has_instance(self, r_type: RegisteredType[Any]) -> bool:
        return (
            r_type.strategy is InjectionStrategy.Scoped
            and r_type.cls in self._scoped_ctx
        ) or (
            r_type.strategy is InjectionStrategy.Singleton
            and r_type.cls in self._global_ctx
        )

    def _get_instance(self, r_type: RegisteredType[T_Instance]) -> T_Instance:
        if r_type.strategy is InjectionStrategy.Scoped:
            return self._scoped_ctx[r_type.cls]
        return self._global_ctx[r_type.cls]

    def _set_instance(
        self, r_type: RegisteredType[T_Instance], instance: T_Instance
    ) -> None:
        if r_type.strategy is InjectionStrategy.Scoped:
            self._scoped_ctx[r_type.cls] = instance
        if r_type.strategy is InjectionStrategy.Singleton:
            self._global_ctx[r_type.cls] = instance
