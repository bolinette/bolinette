import inspect
from collections.abc import Callable, Collection
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Generic,
    Literal,
    ParamSpec,
    Protocol,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

from bolinette import Cache, GenericMeta, __user_cache__, meta
from bolinette.exceptions import InjectionError
from bolinette.types import Type, TypeVarLookup

FuncP = ParamSpec("FuncP")
FuncT = TypeVar("FuncT")
InstanceT = TypeVar("InstanceT")

InjectionSymbol = object()


class _InjectionContext:
    __slots__ = ("_instances",)

    def __init__(self) -> None:
        self._instances: dict[int, Any] = {}

    def has_instance(self, t: Type[Any]) -> bool:
        return hash(t) in self._instances

    def set_instance(self, t: Type[InstanceT], instance: InstanceT) -> None:
        self._instances[hash(t)] = instance

    def get_instance(self, t: Type[InstanceT]) -> InstanceT:
        return self._instances[hash(t)]


class Injection:
    __slots__ = ("_cache", "_global_ctx", "_types", "_arg_resolvers")
    _ADD_INSTANCE_STRATEGIES = ("singleton",)
    _REQUIREABLE_STRATEGIES = ("singleton", "transcient")

    def __init__(
        self,
        cache: Cache,
        global_ctx: _InjectionContext | None = None,
        types: "dict[type[Any], _RegisteredTypeBag[Any]] | None" = None,
    ) -> None:
        self._cache = cache
        self._global_ctx = global_ctx or _InjectionContext()
        self._types = types if types is not None else self._pickup_types(cache)
        self._add_type_instance(Type(Cache), Type(Cache), False, "singleton", [], {}, [], cache, safe=True)
        self._add_type_instance(Type(Injection), Type(Injection), False, "singleton", [], {}, [], self, safe=True)
        self._arg_resolvers = [_DefaultArgResolver()]
        self._arg_resolvers = self._pickup_resolvers(cache)

    @property
    def registered_types(self):
        return dict(self._types)

    @staticmethod
    def _pickup_types(cache: Cache) -> "dict[type[Any], _RegisteredTypeBag[Any]]":
        if InjectionSymbol not in cache:
            return {}
        types: dict[type[Any], _RegisteredTypeBag[Any]] = {}
        for cls in cache.get(InjectionSymbol, hint=type):
            t = Type(cls)
            if t.cls not in types:
                types[t.cls] = _RegisteredTypeBag(t.cls)
            type_bag = types[t.cls]
            _meta = meta.get(t.cls, _InjectionParamsMeta)
            if _meta.match_all:
                type_bag.set_match_all(
                    t,
                    _meta.strategy,  # type: ignore
                    _meta.args,
                    _meta.named_args,
                    _meta.init_methods,
                )
            else:
                type_bag.add_type(
                    t,
                    t,
                    _meta.strategy,  # type: ignore
                    _meta.args,
                    _meta.named_args,
                    _meta.init_methods,
                )
        return types

    def _pickup_resolvers(self, cache: Cache) -> "list[ArgumentResolver]":
        resolver_scoped: dict[type, bool] = {}
        resolver_priority: dict[type, int] = {}
        resolver_types: list[type[ArgumentResolver]] = []

        for t in cache.get(ArgumentResolver, hint=type[ArgumentResolver], raises=False):
            _meta = meta.get(t, _ArgResolverMeta)
            resolver_priority[t] = _meta.priority
            resolver_scoped[t] = _meta.scoped
            resolver_types.append(t)
        resolver_types = sorted(resolver_types, key=lambda t: resolver_priority[t])

        resolvers: list[ArgumentResolver] = []
        for cls in resolver_types:
            if resolver_scoped[cls]:
                continue
            t = Type(cls)
            r_type = _RegisteredType(t, "singleton", [], {}, [])
            resolvers.append(self._instanciate(r_type, t))

        return [*resolvers, _DefaultArgResolver()]

    def _has_instance(self, r_type: "_RegisteredType[Any]") -> bool:
        return r_type.strategy == "singleton" and self._global_ctx.has_instance(r_type.t)

    def _get_instance(self, r_type: "_RegisteredType[InstanceT]") -> InstanceT:
        return self._global_ctx.get_instance(r_type.t)

    def _set_instance(self, r_type: "_RegisteredType[InstanceT]", instance: InstanceT) -> None:
        if r_type.strategy == "singleton":
            self._global_ctx.set_instance(r_type.t, instance)

    def _resolve_args(
        self,
        func: Callable,
        func_type_vars: tuple[Any, ...] | None,
        strategy: Literal["singleton", "scoped", "transcient"],
        vars_lookup: TypeVarLookup[Any] | None,
        immediate: bool,
        args: list[Any],
        named_args: dict[str, Any],
    ) -> dict[str, Any]:
        func_params = dict(inspect.signature(func).parameters)
        if any((n, p) for n, p in func_params.items() if p.kind in (p.POSITIONAL_ONLY, p.VAR_POSITIONAL)):
            raise InjectionError(
                "Positional only parameters and positional wildcards are not allowed",
                func=func,
            )

        f_args: dict[str, Any] = {}
        _args = [*args]
        _named_args = {**named_args}

        try:
            if inspect.isclass(func):
                hints = get_type_hints(func.__init__)
            else:
                hints = get_type_hints(func)
        except NameError as exp:
            raise InjectionError(f"Type hint '{exp.name}' could not be resolved", func=func) from exp

        for p_name, param in func_params.items():
            if param.kind == param.VAR_KEYWORD:
                for kw_name, kw_value in _named_args.items():
                    f_args[kw_name] = kw_value
                _named_args = {}
                break

            if _args:
                f_args[p_name] = _args.pop(0)
                continue
            if p_name in _named_args:
                f_args[p_name] = _named_args.pop(p_name)
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
                raise InjectionError("Annotation is required", func=func, param=p_name)

            hint = hints[p_name]  # type: type

            if get_origin(hint) in (UnionType, Union):
                type_args = get_args(hint)
                nullable = type(None) in type_args
                if not nullable or (nullable and len(type_args) >= 3):
                    raise InjectionError("Type unions are not allowed", func=func, param=p_name)
                hint = next(filter(lambda t: t is not NoneType, type_args))

            hint_t = Type(hint, lookup=vars_lookup)

            for resolver in self._arg_resolvers:
                options = ArgResolverOptions(
                    self,
                    func,
                    func_type_vars,
                    strategy,
                    p_name,
                    hint_t,
                    nullable,
                    default_set,
                    default,
                    immediate,
                )
                if resolver.supports(options):
                    arg_name, arg_value = resolver.resolve(options)
                    f_args[arg_name] = arg_value
                    break

        if _args or _named_args:
            raise InjectionError(
                f"Expected {len(func_params)} arguments, {len(args) + len(named_args)} given",
                func=func,
            )

        return f_args

    def _hook_proxies(self, instance: Any) -> None:
        hooks: dict[str, Type[Any]] = {}
        cls = type(instance)
        cls_attrs = dict(vars(cls))
        for name, attr in cls_attrs.items():
            if isinstance(attr, _InjectionHook):
                delattr(cls, name)
                hooks[name] = attr.t
        instance_attrs = dict(vars(instance))
        for name, attr in instance_attrs.items():
            if isinstance(attr, _InjectionHook):
                delattr(instance, name)
                hooks[name] = attr.t
        for name, t in hooks.items():
            r_type = self._types[t.cls].get_type(t)
            setattr(cls, name, _InjectionProxy(name, r_type, t))

    def _run_init_recursive(
        self,
        cls: type[InstanceT],
        instance: InstanceT,
        vars_lookup: TypeVarLookup[InstanceT] | None,
    ) -> None:
        for base in cls.__bases__:
            self._run_init_recursive(base, instance, vars_lookup)
        for _, attr in vars(cls).items():
            if meta.has(attr, _InitMethodMeta):
                self.call(attr, args=[instance], vars_lookup=vars_lookup)

    def _run_init_methods(
        self,
        r_type: "_RegisteredType[InstanceT]",
        instance: InstanceT,
        vars_lookup: TypeVarLookup[InstanceT] | None,
    ):
        try:
            self._run_init_recursive(r_type.t.cls, instance, vars_lookup)
            for method in r_type.init_methods:
                self.call(method, args=[instance])
        except RecursionError as exp:
            raise InjectionError(
                "Maximum recursion reached while running init method, possible circular dependence", cls=r_type.t.cls
            ) from exp

    def _instanciate(self, r_type: "_RegisteredType[InstanceT]", t: Type[InstanceT]) -> InstanceT:
        vars_lookup = TypeVarLookup(t)
        func_args = self._resolve_args(
            r_type.t.cls,
            t.vars,
            r_type.strategy,  # type: ignore
            vars_lookup,
            False,
            r_type.args,
            r_type.named_args,
        )
        instance = r_type.t.cls(**func_args)
        self._hook_proxies(instance)
        meta.set(instance, self, cls=Injection)
        meta.set(instance, GenericMeta(t.vars))
        self._run_init_methods(r_type, instance, vars_lookup)
        self._set_instance(r_type, instance)
        return instance

    def is_registered(self, cls: type[Any] | Type[Any]) -> bool:
        if not isinstance(cls, Type):
            t = Type(cls)
        else:
            t = cls
        return t.cls in self._types and self._types[t.cls].is_registered(t)

    def call(
        self,
        func: Callable[..., FuncT],
        *,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        vars_lookup: TypeVarLookup[Any] | None = None,
    ) -> FuncT:
        func_args = self._resolve_args(func, None, "singleton", vars_lookup, True, args or [], named_args or {})
        return func(**func_args)

    def instanciate(
        self,
        cls: type[InstanceT],
        *,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
    ) -> InstanceT:
        t = Type(cls)
        init_args = self._resolve_args(cls, t.vars, "transcient", None, True, args or [], named_args or {})
        instance = cls(**init_args)
        self._hook_proxies(instance)
        meta.set(instance, self, cls=Injection)
        meta.set(instance, GenericMeta(t.vars))
        try:
            self._run_init_recursive(cls, instance, None)
        except RecursionError as exp:
            raise InjectionError(
                "Maximum recursion reached while running init method, possible circular dependence", cls=cls
            ) from exp
        return instance

    def _add_type_instance(
        self,
        super_t: Type[InstanceT],
        t: Type[InstanceT],
        match_all: bool,
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any],
        named_args: dict[str, Any],
        init_methods: list[Callable[[InstanceT], None]],
        instance: InstanceT | None,
        *,
        safe: bool = False,
    ) -> None:
        if super_t.cls not in self._types:
            self._types[super_t.cls] = _RegisteredTypeBag(super_t)
        type_bag = self._types[super_t.cls]
        r_type: _RegisteredType[InstanceT] | None = None
        if match_all:
            if not safe or not type_bag.has_match_all():
                r_type = type_bag.set_match_all(t, strategy, args, named_args, init_methods)
        else:
            if not safe or not type_bag.has_type(super_t):
                r_type = type_bag.add_type(super_t, t, strategy, args, named_args, init_methods)
        if instance is not None:
            if r_type is None:
                r_type = self._types[t.cls].get_type(t)
            if not safe or not self._has_instance(r_type):
                self._set_instance(r_type, instance)

    @overload
    def add(
        self,
        cls: type[InstanceT],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        init_methods: list[Callable[[InstanceT], None]] | None = None,
        match_all: bool = False,
        super_cls: type[InstanceT] | None = None,
        *,
        instanciate: Literal[True],
    ) -> InstanceT:
        pass

    @overload
    def add(
        self,
        cls: type[InstanceT],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        init_methods: list[Callable[[InstanceT], None]] | None = None,
        match_all: bool = False,
        super_cls: type[InstanceT] | None = None,
    ) -> None:
        pass

    def add(
        self,
        cls: type[InstanceT],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        init_methods: list[Callable[[InstanceT], None]] | None = None,
        match_all: bool = False,
        super_cls: type[InstanceT] | None = None,
        *,
        instanciate: bool = False,
    ) -> InstanceT | None:
        if super_cls is None:
            super_cls = cls
        t = Type(cls)
        if hasattr(t.cls, "__parameters__"):
            if TYPE_CHECKING:
                assert isinstance(t.cls, _GenericOrigin)
            if len(t.cls.__parameters__) != len(t.vars) and not match_all:
                raise InjectionError(
                    f"Type {t} requires {len(t.cls.__parameters__)} generic parameters and {len(t.vars)} were given"
                )
        super_t = Type(super_cls)
        if not issubclass(t.cls, super_t.cls):
            raise InjectionError(f"Type {t} does not inherit from type {super_t}")
        if instance is not None:
            if instanciate:
                raise InjectionError(
                    f"Cannot instanciate {t.cls} if an instance is provided",
                )
            if not isinstance(instance, t.cls):
                raise InjectionError(f"Object provided must an instance of type {t.cls}")
            if strategy not in self._ADD_INSTANCE_STRATEGIES:
                formatted_strategies = _format_list(self._ADD_INSTANCE_STRATEGIES, final_sep=" or ")
                raise InjectionError(
                    f"Injection strategy for {t.cls} must be {formatted_strategies} if an instance is provided"
                )
        self._add_type_instance(
            super_t, t, match_all, strategy, args or [], named_args or {}, init_methods or [], instance
        )
        if instanciate:
            return self.require(t.cls)
        return None

    def require(self, cls: type[InstanceT]) -> InstanceT:
        t = Type(cls)
        if not self.is_registered(t):
            raise InjectionError(f"Type {t} is not a registered type in the injection system")
        r_type = self._types[t.cls].get_type(t)
        if r_type.strategy not in self._REQUIREABLE_STRATEGIES:
            formatted_strategies = _format_list(self._REQUIREABLE_STRATEGIES, final_sep=" or ")
            raise InjectionError(
                f"Injection strategy for {t} must be {formatted_strategies} to be required in this context"
            )
        if self._has_instance(r_type):
            return self._get_instance(r_type)
        return self._instanciate(r_type, t)

    def get_scoped_session(self) -> "_ScopedInjection":
        return _ScopedInjection(self._cache, self._global_ctx, _InjectionContext(), self._types)


class _DefaultArgResolver:
    __slots__ = ()

    def supports(self, options: "ArgResolverOptions") -> bool:
        return True

    def resolve(self, options: "ArgResolverOptions") -> tuple[str, Any]:
        if not options.injection.is_registered(options.t):
            if options.nullable:
                return (options.name, None)
            if options.default_set:
                return (options.name, options.default)
            raise InjectionError(
                f"Type {options.t} is not a registered type in the injection system",
                func=options.caller,
                param=options.name,
            )

        r_type = options.injection._types[options.t.cls].get_type(options.t)

        if r_type.strategy == "scoped":
            if options.caller_strategy is None:
                raise InjectionError(
                    "Cannot instanciate a scoped service in a non-scoped context",
                    func=options.caller,
                    param=options.name,
                )
            if options.caller_strategy in ["singleton", "transcient"]:
                raise InjectionError(
                    f"Cannot instanciate a scoped service in a {options.caller_strategy} service",
                    func=options.caller,
                    param=options.name,
                )

        if options.injection._has_instance(r_type):
            return (options.name, options.injection._get_instance(r_type))
        if options.immediate:
            return (
                options.name,
                options.injection._instanciate(r_type, options.t),
            )
        return (options.name, _InjectionHook(options.t))


class _InjectionHook(Generic[InstanceT]):
    __slots__ = ("t",)

    def __init__(self, t: Type[InstanceT]) -> None:
        self.t = t

    def __getattribute__(self, __name: str) -> Any:
        if __name in ("t", "__class__"):
            return object.__getattribute__(self, __name)
        raise InjectionError(
            f"Tried accessing member '{__name}' of an injected instance inside the __init__ method. "
            "Use @init_method to process logic at instanciation."
        )

    def __get__(self, *_) -> InstanceT:
        return None  # type: ignore


class _InjectionProxy:
    __slots__ = ("name", "r_type", "t")

    def __init__(
        self,
        name: str,
        r_type: "_RegisteredType[InstanceT]",
        t: Type[InstanceT],
    ) -> None:
        self.name = name
        self.r_type = r_type
        self.t = t

    def __get__(self, instance: Any, _) -> Any:
        inject = meta.get(instance, Injection)
        if inject._has_instance(self.r_type):
            obj = inject._get_instance(self.r_type)
        else:
            obj = inject._instanciate(self.r_type, self.t)
        setattr(instance, self.name, obj)
        return obj


class _ScopedInjection(Injection):
    __slots__ = "_scoped_ctx"

    _ADD_INSTANCE_STRATEGIES = ("singleton", "scoped")
    _REQUIREABLE_STRATEGIES = ("singleton", "scoped", "transcient")

    def __init__(
        self,
        cache: Cache,
        global_ctx: _InjectionContext,
        scoped_ctx: _InjectionContext,
        types: "dict[type[Any], _RegisteredTypeBag[Any]]",
    ) -> None:
        self._scoped_ctx = scoped_ctx
        super().__init__(cache, global_ctx, types)
        self._scoped_ctx.set_instance(Type(Injection), self)

    def _has_instance(self, r_type: "_RegisteredType[Any]") -> bool:
        return (r_type.strategy == "scoped" and self._scoped_ctx.has_instance(r_type.t)) or (
            r_type.strategy == "singleton" and self._global_ctx.has_instance(r_type.t)
        )

    def _get_instance(self, r_type: "_RegisteredType[InstanceT]") -> InstanceT:
        if self._scoped_ctx.has_instance(r_type.t):
            return self._scoped_ctx.get_instance(r_type.t)
        return self._global_ctx.get_instance(r_type.t)

    def _set_instance(self, r_type: "_RegisteredType[InstanceT]", instance: InstanceT) -> None:
        strategy = r_type.strategy
        if strategy == "scoped":
            self._scoped_ctx.set_instance(r_type.t, instance)
        if strategy == "singleton":
            self._global_ctx.set_instance(r_type.t, instance)

    def _pickup_resolvers(self, cache: Cache) -> "list[ArgumentResolver]":
        resolver_scoped: dict[type, bool] = {}
        resolver_priority: dict[type, int] = {}
        resolver_types: list[type[ArgumentResolver]] = []

        for t in cache.get(ArgumentResolver, hint=type[ArgumentResolver], raises=False):
            _meta = meta.get(t, _ArgResolverMeta)
            resolver_priority[t] = _meta.priority
            resolver_scoped[t] = _meta.scoped
            resolver_types.append(t)
        resolver_types = sorted(resolver_types, key=lambda t: resolver_priority[t])

        resolvers: list[ArgumentResolver] = []
        for cls in resolver_types:
            strategy = "scoped" if resolver_scoped[cls] else "singleton"
            t = Type(cls)
            r_type = _RegisteredType(t, strategy, [], {}, [])
            resolvers.append(self._instanciate(r_type, t))

        return [*resolvers, _DefaultArgResolver()]

    def call(
        self,
        func: Callable[..., FuncT],
        *,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        vars_lookup: TypeVarLookup | None = None,
    ) -> FuncT:
        func_args = self._resolve_args(func, None, "scoped", vars_lookup, True, args or [], named_args or {})
        return func(**func_args)


class _RegisteredType(Generic[InstanceT]):
    __slots__ = ("t", "strategy", "args", "named_args", "init_methods")

    def __init__(
        self,
        t: Type[InstanceT],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any],
        named_args: dict[str, Any],
        init_methods: list[Callable[[Any], None]],
    ) -> None:
        self.t = t
        self.strategy = strategy
        self.args = args
        self.named_args = named_args
        self.init_methods = init_methods

    def __repr__(self) -> str:
        return f"<RegisteredType {self.t}: {self.strategy}>"


class _RegisteredTypeBag(Generic[InstanceT]):
    __slots__ = ("_cls", "_match_all", "_types")

    def __init__(self, cls: type[InstanceT]) -> None:
        self._cls = cls
        self._match_all: _RegisteredType[InstanceT] | None = None
        self._types: dict[int, _RegisteredType[InstanceT]] = {}

    def has_type(self, t: Type[InstanceT]) -> bool:
        return hash(t) in self._types

    def has_match_all(self) -> bool:
        return self._match_all is not None

    def is_registered(self, t: Type[InstanceT]) -> bool:
        return self.has_type(t) or self.has_match_all()

    def get_type(self, t: Type[Any]) -> _RegisteredType[InstanceT]:
        if (h := hash(t)) in self._types:
            return self._types[h]
        if self._match_all is not None:
            return self._match_all
        raise InjectionError(f"Type {self._cls} has not been registered with parameters {t.vars}")

    def set_match_all(
        self,
        t: Type[InstanceT],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any],
        named_args: dict[str, Any],
        init_methods: list[Callable[[Any], None]],
    ) -> _RegisteredType[InstanceT]:
        r_type = _RegisteredType(t, strategy, args, named_args, init_methods)
        self._match_all = r_type
        return r_type

    def add_type(
        self,
        super_t: Type[InstanceT],
        t: Type[InstanceT],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any],
        named_args: dict[str, Any],
        init_methods: list[Callable[[Any], None]],
    ) -> _RegisteredType[InstanceT]:
        r_type = _RegisteredType(t, strategy, args, named_args, init_methods)
        self._types[hash(super_t)] = r_type
        return r_type

    def __repr__(self) -> str:
        return f"<RegisteredTypeBag {self._cls}: [{self._match_all}], [{len(self._types)}]>"


class _InitMethodMeta:
    pass


def init_method(func: Callable[Concatenate[InstanceT, FuncP], None]) -> Callable[Concatenate[InstanceT, FuncP], None]:
    meta.set(func, _InitMethodMeta())
    return func


class _InjectionParamsMeta:
    __slots__ = ("strategy", "args", "named_args", "init_methods", "match_all")

    def __init__(
        self,
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any] | None,
        named_args: dict[str, Any] | None,
        init_methods: list[Callable[[Any], None]] | None,
        match_all: bool,
    ) -> None:
        self.strategy = strategy
        self.args = args or []
        self.named_args = named_args or {}
        self.init_methods = init_methods or []
        self.match_all = match_all


def injectable(
    *,
    strategy: Literal["singleton", "scoped", "transcient"] = "singleton",
    args: list[Any] | None = None,
    named_args: dict[str, Any] | None = None,
    cache: Cache | None = None,
    init_methods: list[Callable[[InstanceT], None]] | None = None,
    match_all: bool = False,
) -> Callable[[type[InstanceT]], type[InstanceT]]:
    def decorator(cls: type[InstanceT]) -> type[InstanceT]:
        if origin := get_origin(cls):
            _cls = origin
        else:
            _cls = cls
        meta.set(_cls, _InjectionParamsMeta(strategy, args, named_args, init_methods, match_all))
        (cache or __user_cache__).add(InjectionSymbol, cls)
        return cls

    return decorator


def require(cls: type[InstanceT]) -> Callable[[Callable], _InjectionHook[InstanceT]]:
    def decorator(func: Callable) -> _InjectionHook[InstanceT]:
        return _InjectionHook(Type(cls))

    return decorator


class ArgResolverOptions:
    __slots__ = (
        "injection",
        "caller",
        "caller_type_vars",
        "caller_strategy",
        "name",
        "t",
        "nullable",
        "default_set",
        "default",
        "immediate",
    )

    def __init__(
        self,
        injection: Injection,
        caller: Callable,
        caller_type_vars: tuple[Any, ...] | None,
        caller_strategy: Literal["singleton", "scoped", "transcient"] | None,
        name: str,
        t: Type[Any],
        nullable: bool,
        default_set: bool,
        default: Any | None,
        immediate: bool,
    ) -> None:
        self.injection = injection
        self.caller = caller
        self.caller_type_vars = caller_type_vars
        self.caller_strategy = caller_strategy
        self.name = name
        self.t = t
        self.nullable = nullable
        self.default_set = default_set
        self.default = default
        self.immediate = immediate


class ArgumentResolver(Protocol):
    def supports(self, options: ArgResolverOptions) -> bool:
        ...

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        ...


class _ArgResolverMeta:
    __slots__ = ("priority", "scoped")

    def __init__(self, priority: int, scoped: bool) -> None:
        self.priority = priority
        self.scoped = scoped


ArgResolverT = TypeVar("ArgResolverT", bound=ArgumentResolver)


def injection_arg_resolver(
    *, priority: int = 0, scoped: bool = False, cache: Cache | None = None
) -> Callable[[type[ArgResolverT]], type[ArgResolverT]]:
    def decorator(cls: type[ArgResolverT]) -> type[ArgResolverT]:
        (cache or __user_cache__).add(ArgumentResolver, cls)
        meta.set(cls, _ArgResolverMeta(priority, scoped))
        return cls

    return decorator


class _GenericOrigin(Protocol):
    __parameters__: tuple[TypeVar, ...]


def _format_list(collection: Collection[Any], *, sep: str = ", ", final_sep: str | None = None) -> str:
    """TODO: move this into StringUtils and rework import flow"""
    formatted = []
    cnt = len(collection)
    for i, e in enumerate(collection):
        formatted.append(str(e))
        if i != cnt - 1:
            if i == cnt - 2:
                formatted.append(final_sep)
            else:
                formatted.append(sep)
    return "".join(formatted)
