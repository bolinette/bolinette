import inspect
from collections.abc import Callable
import re
from types import UnionType
from typing import (
    Any,
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from bolinette.core import Cache, InjectionStrategy, meta
from bolinette.core.cache import RegisteredType
from bolinette.core.exceptions import InitError, InjectionError


class _InitMethodMeta:
    pass


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
            raise InjectionError(
                f"Type {cls} has already been instanciated in this scope"
            )
        if not isinstance(instance, cls):
            raise TypeError("Object is not an instance of cls")
        self._instances[cls] = instance

    def __getitem__(self, cls: type[T_Instance]) -> T_Instance:
        if cls not in self:
            raise InjectionError(f"Type {cls} has not been instanciated in this scope")
        return self._instances[cls]


class Injection:
    _LEFT_NONE_TYPE_REGEX = re.compile(r"^ *None *\| *([^\| ]+) *$")
    _RIGHT_NONE_TYPE_REGEX = re.compile(r"^ *([^\| ]+) *\| *None *$")
    _OPTIONAL_TYPE_REGEX = re.compile(r"^ *Optional\[([^\]]+)\] *$")

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
            raise InjectionError(
                f"Cannot instanciate a scoped service outside of a scoped session",
                cls=r_type.cls,
            )
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
            raise InjectionError(
                f"Positional only parameters and positional wildcards are not allowed",
                func=func,
            )

        f_args: dict[str, Any] = {}
        _args = [*args]
        _kwargs = {**kwargs}

        for p_name, param in params.items():
            if param.kind == param.VAR_KEYWORD:
                for kw_name, kw_value in _kwargs.items():
                    f_args[kw_name] = kw_value
                _kwargs = {}
                break

            if _args:
                f_args[p_name] = _args.pop(0)
                continue
            if p_name in _kwargs:
                f_args[p_name] = _kwargs.pop(p_name)
                continue

            default_set = False
            default = None
            if param.default is not param.empty:
                default_set = True
                default = param.default
            hint = param.annotation
            nullable = False

            if hint == inspect.Signature.empty:
                if default_set:
                    f_args[p_name] = default
                    continue
                raise InjectionError(f"Annotation is required", func=func, param=p_name)

            if get_origin(hint) in [UnionType, Union]:
                type_args = get_args(hint)
                nullable = type(None) in type_args
                if not nullable or (nullable and len(type_args) >= 3):
                    raise InjectionError(
                        f"Type unions are not allowed", func=func, param=p_name
                    )
                hint = next(filter(lambda t: t is not type(None), type_args))

            if isinstance(hint, str):
                if (
                    (match_right := self._RIGHT_NONE_TYPE_REGEX.match(hint))
                    or (match_left := self._LEFT_NONE_TYPE_REGEX.match(hint))
                    or (match_opt := self._OPTIONAL_TYPE_REGEX.match(hint))
                ):
                    nullable = True
                    if match_right:
                        hint = match_right.group(1)
                    elif match_left:
                        hint = match_left.group(1)
                    elif match_opt:
                        hint = match_opt.group(1)

            if isinstance(hint, type) or isinstance(hint, str):
                cls: type[Any] | None = None
                if isinstance(hint, str):
                    classes = self._cache.find_types_by_name(hint)
                    if not classes:
                        if nullable:
                            f_args[p_name] = None
                            break
                        raise InjectionError(
                            f"Literal '{hint}' does not match any registered type",
                            func=func,
                            param=p_name,
                        )
                    if (l := len(classes)) > 1:
                        raise InjectionError(
                            f"Literal '{hint}' matches with {l} registered types, use a more explicit name",
                            func=func,
                            param=p_name,
                        )
                    cls = classes[0]
                else:
                    cls = hint
                if not self._cache.has_type(cls):
                    if nullable:
                        f_args[p_name] = None
                        continue
                    if default_set:
                        f_args[p_name] = default
                        continue
                    raise InjectionError(
                        f"Type {cls} is not a registered type in the injection system"
                    )
                else:
                    r_type = self._cache.get_type(cls)
                    if self._has_instance(r_type):
                        f_args[p_name] = self._get_instance(r_type)
                        continue
                    if immediate:
                        f_args[p_name] = self._instanciate(r_type)
                        continue
                    f_args[p_name] = _ProxyHook(r_type)
                    continue
            raise InjectionError(
                f"Callable {func}, Parameter '{p_name}': Type hint is not supported by the injection system"
            )

        if _args or _kwargs:
            raise InjectionError(
                f"Expected {len(params)} arguments, {len(args) + len(kwargs)} given",
                func=func,
            )

        return f_args

    def _hook_proxies(self, instance: Any) -> None:
        cls = type(instance)
        attrs = dict(vars(instance))
        for name, attr in attrs.items():
            if isinstance(attr, _ProxyHook):
                delattr(instance, name)
                setattr(cls, name, _InjectionProxy(name, attr.r_type))

    def _run_init_recursive(self, cls: type[T_Instance], instance: T_Instance):
        for base in cls.__bases__:
            self._run_init_recursive(base, instance)
        for _, attr in vars(cls).items():
            if meta.has(attr, _InitMethodMeta):
                self.call(attr, args=[instance])

    def _run_init_methods(
        self, r_type: RegisteredType[T_Instance], instance: T_Instance
    ):
        self._run_init_recursive(r_type.cls, instance)
        for method in r_type.init_methods:
            self.call(method, args=[instance])

    def _instanciate(
        self,
        r_type: RegisteredType[T_Instance],
    ) -> T_Instance:
        if self._has_instance(r_type):
            raise InjectionError(
                f"Type {r_type.cls} has already been instanciated in this scope"
            )
        func_args = self._resolve_args(r_type.cls, False, r_type.args, r_type.kwargs)
        instance = r_type.cls(**func_args)
        meta.set(instance, Injection, self)
        self._hook_proxies(instance)
        self._run_init_methods(r_type, instance)
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
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        instance: T_Instance | None = None,
        init_methods: list[Callable[[T_Instance], None]] | None = None,
    ) -> None:
        if self._cache.has_type(cls):
            raise InjectionError(f"Type {cls} is already a registered type")
        r_type = self._cache.add_type(cls, strategy, args, kwargs, init_methods)
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
            raise InjectionError(
                f"Type {cls} is not a registered type in the injection system"
            )
        r_type = self._cache.get_type(cls)
        if self._has_instance(r_type):
            return self._get_instance(r_type)
        return self._instanciate(r_type)

    def is_registered(self, cls: type[Any]) -> bool:
        return self._cache.has_type(cls)

    def get_scoped_session(self) -> "_ScopedInjection":
        return _ScopedInjection(self, self._cache, self._global_ctx, InjectionContext())


class _ProxyHook:
    def __init__(self, r_type: RegisteredType[Any]) -> None:
        self.r_type = r_type

    def __getattribute__(self, __name: str) -> Any:
        if __name == "r_type":
            return object.__getattribute__(self, __name)
        raise InjectionError(
            "Tried accessing an injected instance inside the __init__ method. "
            "Use @init_method to process logic at instanciation."
        )


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


def init_method(
    func: Callable[Concatenate[T_Instance, P_Func], None]
) -> Callable[Concatenate[T_Instance, P_Func], None]:
    if not inspect.isfunction(func):
        raise InitError(
            f"{func} must be a function to be decorated by {init_method.__name__}"
        )
    meta.set(func, _InitMethodMeta, _InitMethodMeta())
    return func
