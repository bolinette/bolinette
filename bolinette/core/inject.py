import inspect
import re
from collections.abc import Callable
from types import UnionType
from typing import (
    Any,
    Concatenate,
    ForwardRef,
    Generic,
    Literal,
    ParamSpec,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

from bolinette.core import Cache, GenericMeta, __core_cache__, meta
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
        self._add_safe(Cache, "singleton", self._cache)
        self._add_safe(Injection, "singleton", self)

    def _add_safe(
        self,
        cls: type[T_Instance],
        strategy: Literal["singleton", "scoped", "transcient"],
        instance: T_Instance,
    ):
        if not cls in self._cache.types:
            self.add(cls, strategy)
        if cls not in self._global_ctx:
            self._global_ctx[cls] = instance

    def _has_instance(
        self, cls: type[Any], *, origin: Callable | None = None, name: str | None = None
    ) -> bool:
        strategy = self._cache.types.strategy(cls)
        if strategy == "scoped":
            if origin:
                raise InjectionError(
                    f"Cannot instanciate a scoped service in a non-scoped one",
                    func=origin,
                    param=name,
                )
            raise InjectionError(
                f"Cannot instanciate a scoped service outside of a scoped session",
                cls=cls,
            )
        return strategy == "singleton" and cls in self._global_ctx

    def _get_instance(self, cls: type[T_Instance]) -> T_Instance:
        return self._global_ctx[cls]

    def _set_instance(self, cls: type[T_Instance], instance: T_Instance) -> None:
        if self._cache.types.strategy(cls) == "singleton":
            self._global_ctx[cls] = instance

    def _resolve_args(
        self,
        func: Callable,
        immediate: bool,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        params = dict(inspect.signature(func).parameters)
        if any(
            (n, p)
            for n, p in params.items()
            if p.kind in (p.POSITIONAL_ONLY, p.VAR_POSITIONAL)
        ):
            raise InjectionError(
                f"Positional only parameters and positional wildcards are not allowed",
                func=func,
            )

        f_args: dict[str, Any] = {}
        _args = [*args]
        _kwargs = {**kwargs}

        try:
            if inspect.isclass(func):
                hints = get_type_hints(func.__init__)
            else:
                hints = get_type_hints(func)
        except NameError as e:
            raise InjectionError(
                f"Type hint '{e.name}' could not be resolved", func=func
            )

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
            nullable = False

            if p_name not in hints:
                if default_set:
                    f_args[p_name] = default
                    continue
                raise InjectionError(f"Annotation is required", func=func, param=p_name)

            hint = hints[p_name]  # type: type

            if get_origin(hint) in (UnionType, Union):
                type_args = get_args(hint)
                nullable = type(None) in type_args
                if not nullable or (nullable and len(type_args) >= 3):
                    raise InjectionError(
                        f"Type unions are not allowed", func=func, param=p_name
                    )
                hint = next(filter(lambda t: t is not type(None), type_args))

            hint, templates = self._get_generic_templates(hint)

            if not hint in self._cache.types:
                if nullable:
                    f_args[p_name] = None
                    continue
                if default_set:
                    f_args[p_name] = default
                    continue
                raise InjectionError(
                    f"Type {hint} is not a registered type in the injection system",
                    func=func,
                    param=p_name,
                )
            else:
                if self._has_instance(hint, origin=func, name=p_name):
                    f_args[p_name] = self._get_instance(hint)
                    continue
                if immediate:
                    f_args[p_name] = self._instanciate(hint, templates)
                    continue
                f_args[p_name] = _ProxyHook(hint, templates)
                continue

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
                setattr(cls, name, _InjectionProxy(name, attr.cls, attr.templates))

    def _run_init_recursive(self, cls: type[T_Instance], instance: T_Instance) -> None:
        for base in cls.__bases__:
            self._run_init_recursive(base, instance)
        for _, attr in vars(cls).items():
            if meta.has(attr, _InitMethodMeta):
                self.call(attr, args=[instance])

    def _run_init_methods(self, cls: type[T_Instance], instance: T_Instance):
        self._run_init_recursive(cls, instance)
        for method in self._cache.types.init_methods(cls):
            self.call(method, args=[instance])

    @staticmethod
    def _get_generic_templates(
        _cls: type[T_Instance],
    ) -> tuple[type[T_Instance], list[type[Any]]]:
        if origin := get_origin(_cls):
            templates = []
            for arg in get_args(_cls):
                if isinstance(arg, ForwardRef):
                    raise InjectionError(
                        f"Generic parameter {arg}, literal type hints are not allowed in direct require calls",
                        cls=origin,
                    )
                templates.append(arg)
            return origin, templates  # type: ignore
        return _cls, []

    def _instanciate(
        self, cls: type[T_Instance], templates: list[Any] | None = None
    ) -> T_Instance:
        if self._has_instance(cls):
            raise InjectionError(
                f"Type {cls} has already been instanciated in this scope"
            )
        func_args = self._resolve_args(
            cls, False, self._cache.types.args(cls), self._cache.types.kwargs(cls)
        )
        instance = cls(**func_args)
        meta.set(instance, self, cls=Injection)
        self._hook_proxies(instance)
        if templates:
            meta.set(instance, GenericMeta(templates))
        self._run_init_methods(cls, instance)
        self._set_instance(cls, instance)
        return instance

    def call(
        self,
        func: Callable[..., T_Func],
        *,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> T_Func:
        func_args = self._resolve_args(func, True, args or [], kwargs or {})
        return func(**func_args)

    @overload
    def add(
        self,
        cls: type[T_Instance],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        instance: T_Instance | None = None,
        init_methods: list[Callable[[T_Instance], None]] | None = None,
        *,
        instanciate: Literal[True],
    ) -> T_Instance:
        pass

    @overload
    def add(
        self,
        cls: type[T_Instance],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        instance: T_Instance | None = None,
        init_methods: list[Callable[[T_Instance], None]] | None = None,
        *,
        instanciate: Literal[False] = False,
    ) -> None:
        pass

    def add(
        self,
        cls: type[T_Instance],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        instance: T_Instance | None = None,
        init_methods: list[Callable[[T_Instance], None]] | None = None,
        *,
        instanciate: bool = False,
    ) -> T_Instance | None:
        if cls in self._cache.types:
            raise InjectionError(f"Type {cls} is already a registered type")
        self._cache.types.add(cls, strategy, args, kwargs, init_methods)
        if instance is not None:
            if instanciate:
                raise InjectionError(
                    f"Cannot instanciate {cls} if an instance is provided"
                )
            if not isinstance(instance, cls):
                raise InjectionError(f"Object provided must an instance of type {cls}")
            if strategy != "singleton":
                raise InjectionError(
                    f"Type {cls} must be a singleton if an instance is provided"
                )
            self._set_instance(cls, instance)
        if instanciate:
            return self.require(cls)
        return None

    def require(self, cls: type[T_Instance]) -> T_Instance:
        cls, templates = self._get_generic_templates(cls)
        if not cls in self._cache.types:
            raise InjectionError(
                f"Type {cls} is not a registered type in the injection system"
            )
        if self._has_instance(cls):
            return self._get_instance(cls)
        return self._instanciate(cls, templates)

    def is_registered(self, cls: type[Any]) -> bool:
        return cls in self._cache.types

    def get_scoped_session(self) -> "_ScopedInjection":
        return _ScopedInjection(self, self._cache, self._global_ctx, InjectionContext())


class _ProxyHook:
    def __init__(self, cls: type[Any], templates: list[Any] | None = None) -> None:
        self.cls = cls
        self.templates = templates

    def __getattribute__(self, __name: str) -> Any:
        if __name in ("cls", "templates"):
            return object.__getattribute__(self, __name)
        raise InjectionError(
            "Tried accessing an injected instance inside the __init__ method. "
            "Use @init_method to process logic at instanciation."
        )


class _InjectionProxy(Generic[T_Instance]):
    def __init__(
        self,
        name: str,
        cls: type[T_Instance],
        templates: list[Any] | None = None,
    ) -> None:
        self._name = name
        self._cls = cls
        self._templates = templates

    def __get__(self, instance: Any, _) -> T_Instance:
        if not meta.has(instance, Injection):
            raise InjectionError(
                f"{instance} has not been intanciated through the injection system"
            )
        inject = meta.get(instance, Injection)
        obj: T_Instance
        if inject._has_instance(self._cls):
            obj = inject._get_instance(self._cls)
        else:
            obj = inject._instanciate(self._cls, self._templates)
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

    def _has_instance(self, cls: type[Any], **_) -> bool:
        strategy = self._cache.types.strategy(cls)
        return (strategy == "scoped" and cls in self._scoped_ctx) or (
            strategy == "singleton" and cls in self._global_ctx
        )

    def _get_instance(self, cls: type[T_Instance]) -> T_Instance:
        if cls in self._scoped_ctx:
            return self._scoped_ctx[cls]
        return self._global_ctx[cls]

    def _set_instance(self, cls: type[T_Instance], instance: T_Instance) -> None:
        strategy = self._cache.types.strategy(cls)
        if strategy == "scoped":
            self._scoped_ctx[cls] = instance
        if strategy == "singleton":
            self._global_ctx[cls] = instance


def init_method(
    func: Callable[Concatenate[T_Instance, P_Func], None]
) -> Callable[Concatenate[T_Instance, P_Func], None]:
    meta.set(func, _InitMethodMeta())
    return func


def injectable(
    *,
    strategy: Literal["singleton", "scoped", "transcient"] = "singleton",
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    cache: Cache | None = None,
) -> Callable[[type[T_Instance]], type[T_Instance]]:
    def decorator(cls: type[T_Instance]) -> type[T_Instance]:
        (cache or __core_cache__).types.add(cls, strategy, args, kwargs)
        return cls

    return decorator


def require(cls: type[T_Instance]) -> Callable[[Callable], _InjectionProxy[T_Instance]]:
    def decorator(func: Callable) -> _InjectionProxy[T_Instance]:
        _cls, templates = Injection._get_generic_templates(cls)
        return _InjectionProxy(func.__name__, _cls, templates)

    return decorator
