import inspect
from collections.abc import Callable
from types import NoneType, UnionType
from typing import (
    Any,
    Concatenate,
    ForwardRef,
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

FuncP = ParamSpec("FuncP")
FuncT = TypeVar("FuncT")
InstanceT = TypeVar("InstanceT")

InjectionSymbol = object()


class _InjectionContext:
    def __init__(self) -> None:
        self._instances: dict[type[Any], dict[int, Any]] = {}

    def has_instance(self, cls: type[Any], params: tuple[Any, ...]) -> bool:
        return cls in self._instances and hash(params) in self._instances[cls]

    def set_instance(
        self, cls: type[Any], params: tuple[Any, ...], instance: Any
    ) -> None:
        if cls not in self._instances:
            self._instances[cls] = {}
        self._instances[cls][hash(params)] = instance

    def get_instance(self, cls: type[InstanceT], params: tuple[Any, ...]) -> InstanceT:
        return self._instances[cls][hash(params)]


class Injection:
    def __init__(
        self,
        cache: Cache,
        global_ctx: _InjectionContext | None = None,
        types: "dict[type[Any], _RegisteredTypeBag[Any]] | None" = None,
    ) -> None:
        self._cache = cache
        self._global_ctx = global_ctx or _InjectionContext()
        self._types = types if types is not None else self._pickup_types(cache)
        self._add_type_instance(
            Cache, (), Cache, (), False, "singleton", [], {}, [], cache, safe=True
        )
        self._add_type_instance(
            Injection,
            (),
            Injection,
            (),
            False,
            "singleton",
            [],
            {},
            [],
            self,
            safe=True,
        )
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
            cls, params = Injection._get_generic_params(cls)
            if cls not in types:
                types[cls] = _RegisteredTypeBag(cls)
            type_bag = types[cls]
            _meta = meta.get(cls, _InjectionParamsMeta)
            if _meta.match_all:
                type_bag.set_match_all(
                    cls,
                    params,
                    _meta.strategy,  # type: ignore
                    _meta.args,
                    _meta.kwargs,
                    _meta.init_methods,
                )
            else:
                type_bag.add_type(
                    params,
                    cls,
                    params,
                    _meta.strategy,  # type: ignore
                    _meta.args,
                    _meta.kwargs,
                    _meta.init_methods,
                )
        return types

    @staticmethod
    def _pickup_resolvers(cache: Cache) -> "list[ArgumentResolver]":
        return [
            *map(
                lambda t: t(),
                sorted(
                    cache.get(
                        ArgumentResolver, hint=type[ArgumentResolver], raises=False
                    ),
                    key=lambda t: meta.get(t, _ArgResolverMeta).priority,
                ),
            ),
            _DefaultArgResolver(),
        ]

    def _has_instance(
        self,
        r_type: "_RegisteredType[Any]",
        *,
        origin: Callable | None = None,
        name: str | None = None,
    ) -> bool:
        if r_type.strategy == "scoped":
            if origin:
                raise InjectionError(
                    "Cannot instanciate a scoped service in a non-scoped one",
                    func=origin,
                    param=name,
                )
            raise InjectionError(
                "Cannot instanciate a scoped service outside of a scoped session",
                cls=r_type.cls,
            )
        return r_type.strategy == "singleton" and self._global_ctx.has_instance(
            r_type.cls, r_type.params
        )

    def _get_instance(self, r_type: "_RegisteredType[InstanceT]") -> InstanceT:
        return self._global_ctx.get_instance(r_type.cls, r_type.params)

    def _set_instance(
        self, r_type: "_RegisteredType[InstanceT]", instance: InstanceT
    ) -> None:
        if r_type.strategy == "singleton":
            self._global_ctx.set_instance(r_type.cls, r_type.params, instance)

    def _resolve_args(
        self,
        func: Callable,
        immediate: bool,
        args: list[Any],
        named_args: dict[str, Any],
    ) -> dict[str, Any]:
        func_params = dict(inspect.signature(func).parameters)
        if any(
            (n, p)
            for n, p in func_params.items()
            if p.kind in (p.POSITIONAL_ONLY, p.VAR_POSITIONAL)
        ):
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
            raise InjectionError(
                f"Type hint '{exp.name}' could not be resolved", func=func
            ) from exp

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
                    raise InjectionError(
                        "Type unions are not allowed", func=func, param=p_name
                    )
                hint = next(filter(lambda t: t is not NoneType, type_args))

            hint, gen_params = self._get_generic_params(hint)

            for resolver in self._arg_resolvers:
                options = ArgResolverOptions(
                    self,
                    func,
                    p_name,
                    hint,
                    gen_params,
                    nullable,
                    default_set,
                    default,
                    immediate,
                )
                if resolver.supports(options):
                    arg_name, arg_value = resolver.resolve(options)
                    f_args[arg_name] = arg_value

        if _args or _named_args:
            raise InjectionError(
                f"Expected {len(func_params)} arguments, {len(args) + len(named_args)} given",
                func=func,
            )

        return f_args

    def _hook_proxies(self, instance: Any) -> None:
        hooks: list[tuple[str, type[Any], tuple[Any, ...]]] = []
        cls = type(instance)
        cls_attrs = dict(vars(cls))
        for name, attr in cls_attrs.items():
            if isinstance(attr, _InjectionHook):
                delattr(cls, name)
                hooks.append((name, attr.cls, attr.params))
        instance_attrs = dict(vars(instance))
        for name, attr in instance_attrs.items():
            if isinstance(attr, _InjectionHook):
                delattr(instance, name)
                hooks.append((name, attr.cls, attr.params))
        for name, _cls, params in hooks:
            r_type = self._types[_cls].get_type(params)
            setattr(cls, name, _InjectionProxy(name, r_type, params))

    def _run_init_recursive(self, cls: type[InstanceT], instance: InstanceT) -> None:
        for base in cls.__bases__:
            self._run_init_recursive(base, instance)
        for _, attr in vars(cls).items():
            if meta.has(attr, _InitMethodMeta):
                self.call(attr, args=[instance])

    def _run_init_methods(
        self, r_type: "_RegisteredType[InstanceT]", instance: InstanceT
    ):
        self._run_init_recursive(r_type.cls, instance)
        for method in r_type.init_methods:
            self.call(method, args=[instance])

    @staticmethod
    def _get_generic_params(
        _cls: type[InstanceT],
    ) -> tuple[type[InstanceT], tuple[Any, ...]]:
        if origin := get_origin(_cls):
            params: tuple[Any, ...] = ()
            for arg in get_args(_cls):
                if isinstance(arg, ForwardRef):
                    raise InjectionError(
                        f"Generic parameter {arg}, literal type hints are not allowed in direct require calls",
                        cls=origin,
                    )
                params = (*params, arg)
            return origin, params
        return _cls, ()

    def _instanciate(
        self, r_type: "_RegisteredType[InstanceT]", params: tuple[Any, ...]
    ) -> InstanceT:
        func_args = self._resolve_args(r_type.cls, False, r_type.args, r_type.kwargs)
        instance = r_type.cls(**func_args)
        self._hook_proxies(instance)
        meta.set(instance, self, cls=Injection)
        meta.set(instance, GenericMeta(params))
        self._run_init_methods(r_type, instance)
        self._set_instance(r_type, instance)
        return instance

    def is_registered(
        self, cls: type[Any], params: tuple[Any, ...] | None = None
    ) -> bool:
        if params is None:
            params = ()
        return cls in self._types and self._types[cls].is_registered(params)

    def call(
        self,
        func: Callable[..., FuncT],
        *,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
    ) -> FuncT:
        func_args = self._resolve_args(func, True, args or [], named_args or {})
        return func(**func_args)

    def _add_type_instance(
        self,
        super_cls: type[InstanceT],
        super_params: tuple[Any, ...],
        cls: type[InstanceT],
        params: tuple[Any, ...],
        match_all: bool,
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any],
        named_args: dict[str, Any],
        init_methods: list[Callable[[InstanceT], None]],
        instance: InstanceT | None,
        *,
        safe: bool = False,
    ) -> None:
        if super_cls not in self._types:
            self._types[super_cls] = _RegisteredTypeBag(super_cls)
        type_bag = self._types[super_cls]
        r_type: _RegisteredType[InstanceT] | None = None
        if match_all:
            if not safe or not type_bag.has_match_all():
                r_type = type_bag.set_match_all(
                    cls, params, strategy, args, named_args, init_methods
                )
        else:
            if not safe or not type_bag.has_type(super_params):
                r_type = type_bag.add_type(
                    super_params, cls, params, strategy, args, named_args, init_methods
                )
        if instance is not None:
            if r_type is None:
                r_type = self._types[cls].get_type(params)
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
        cls, params = self._get_generic_params(cls)
        super_cls, super_params = self._get_generic_params(super_cls)
        if not issubclass(cls, super_cls):
            raise InjectionError(f"Type {cls} does not inherit from type {super_cls}")
        if instance is not None:
            if instanciate:
                raise InjectionError(
                    f"Cannot instanciate {cls} if an instance is provided",
                )
            if not isinstance(instance, cls):
                raise InjectionError(f"Object provided must an instance of type {cls}")
            if strategy != "singleton":
                raise InjectionError(
                    f"Type {cls} must be a singleton if an instance is provided"
                )
        self._add_type_instance(
            super_cls,
            super_params,
            cls,
            params,
            match_all,
            strategy,
            args or [],
            named_args or {},
            init_methods or [],
            instance,
        )
        if instanciate:
            return self.require(cls)
        return None

    def require(self, cls: type[InstanceT]) -> InstanceT:
        cls, params = self._get_generic_params(cls)
        if not self.is_registered(cls, params):
            if len(params):
                error_txt = f"{cls}[{params}]"
            else:
                error_txt = f"{cls}"
            raise InjectionError(
                f"Type {error_txt} is not a registered type in the injection system"
            )
        r_type = self._types[cls].get_type(params)
        if self._has_instance(r_type):
            return self._get_instance(r_type)
        return self._instanciate(r_type, params)

    def get_scoped_session(self) -> "_ScopedInjection":
        return _ScopedInjection(
            self, self._cache, self._global_ctx, _InjectionContext(), self._types
        )


class _DefaultArgResolver:
    def supports(self, options: "ArgResolverOptions") -> bool:
        return True

    def resolve(self, options: "ArgResolverOptions") -> tuple[str, Any]:
        if not options.injection.is_registered(options.cls, options.generic_params):
            if options.nullable:
                return (options.name, None)
            if options.default_set:
                return (options.name, options.default)
            if len(options.generic_params):
                error_txt = f"{options.cls}[{options.generic_params}]"
            else:
                error_txt = f"{options.cls}"
            raise InjectionError(
                f"Type {error_txt} is not a registered type in the injection system",
                func=options.caller,
                param=options.name,
            )

        r_type = options.injection._types[options.cls].get_type(options.generic_params)

        if options.injection._has_instance(
            r_type, origin=options.caller, name=options.name
        ):
            return (options.name, options.injection._get_instance(r_type))
        if options.immediate:
            return (
                options.name,
                options.injection._instanciate(r_type, options.generic_params),
            )
        return (options.name, _InjectionHook(options.cls, options.generic_params))


class _InjectionHook(Generic[InstanceT]):
    def __init__(self, cls: type[Any], params: tuple[Any, ...]) -> None:
        self.cls = cls
        self.params = params

    def __getattribute__(self, __name: str) -> Any:
        if __name in ("cls", "params", "__class__"):
            return object.__getattribute__(self, __name)
        raise InjectionError(
            f"Tried accessing member '{__name  }' of an injected instance inside the __init__ method. "
            "Use @init_method to process logic at instanciation."
        )

    def __get__(self, *_) -> InstanceT:
        return None  # type: ignore


class _InjectionProxy:
    def __init__(
        self,
        name: str,
        r_type: "_RegisteredType[Any]",
        params: tuple[Any, ...],
    ) -> None:
        self.name = name
        self.r_type = r_type
        self.params = params

    def __get__(self, instance: Any, _) -> Any:
        inject = meta.get(instance, Injection)
        if inject._has_instance(self.r_type):
            obj = inject._get_instance(self.r_type)
        else:
            obj = inject._instanciate(self.r_type, self.params)
        setattr(instance, self.name, obj)
        return obj


class _ScopedInjection(Injection):
    def __init__(
        self,
        global_inject: Injection,
        cache: Cache,
        global_ctx: _InjectionContext,
        scoped_ctx: _InjectionContext,
        types: "dict[type[Any], _RegisteredTypeBag[Any]]",
    ) -> None:
        super().__init__(cache, global_ctx, types)
        self._global_inject = global_inject
        self._scoped_ctx = scoped_ctx
        self._scoped_ctx.set_instance(Injection, (), self)

    def _has_instance(self, r_type: "_RegisteredType[Any]", **_) -> bool:
        return (
            r_type.strategy == "scoped"
            and self._scoped_ctx.has_instance(r_type.cls, r_type.params)
        ) or (
            r_type.strategy == "singleton"
            and self._global_ctx.has_instance(r_type.cls, r_type.params)
        )

    def _get_instance(self, r_type: "_RegisteredType[InstanceT]") -> InstanceT:
        if self._scoped_ctx.has_instance(r_type.cls, r_type.params):
            return self._scoped_ctx.get_instance(r_type.cls, r_type.params)
        return self._global_ctx.get_instance(r_type.cls, r_type.params)

    def _set_instance(
        self, r_type: "_RegisteredType[InstanceT]", instance: InstanceT
    ) -> None:
        strategy = r_type.strategy
        if strategy == "scoped":
            self._scoped_ctx.set_instance(r_type.cls, r_type.params, instance)
        if strategy == "singleton":
            self._global_ctx.set_instance(r_type.cls, r_type.params, instance)


class _RegisteredType(Generic[InstanceT]):
    def __init__(
        self,
        cls: type[InstanceT],
        params: tuple[Any, ...],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any],
        named_args: dict[str, Any],
        init_methods: list[Callable[[Any], None]],
    ) -> None:
        self.cls = cls
        self.params = params
        self.strategy = strategy
        self.args = args
        self.kwargs = named_args
        self.init_methods = init_methods

    def __repr__(self) -> str:
        return f"<RegisteredType {self.cls}: {self.strategy}>"


class _RegisteredTypeBag(Generic[InstanceT]):
    def __init__(self, cls: type[InstanceT]) -> None:
        self._cls = cls
        self._match_all: _RegisteredType[InstanceT] | None = None
        self._types: dict[int, _RegisteredType[InstanceT]] = {}

    def has_type(self, params) -> bool:
        return hash(params) in self._types

    def has_match_all(self) -> bool:
        return self._match_all is not None

    def is_registered(self, params: tuple[Any, ...]) -> bool:
        return self.has_type(params) or self.has_match_all()

    def get_type(self, params: tuple[Any, ...]) -> _RegisteredType[InstanceT]:
        if (h := hash(params)) in self._types:
            return self._types[h]
        if self._match_all is not None:
            return self._match_all
        raise InjectionError(
            f"Type {self._cls} has not been registered with parameters {params}"
        )

    def set_match_all(
        self,
        cls: type[InstanceT],
        params: tuple[Any, ...],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any],
        named_args: dict[str, Any],
        init_methods: list[Callable[[Any], None]],
    ) -> _RegisteredType[InstanceT]:
        r_type = _RegisteredType(cls, params, strategy, args, named_args, init_methods)
        self._match_all = r_type
        return r_type

    def add_type(
        self,
        super_params: tuple[Any, ...],
        cls: type[InstanceT],
        params: tuple[Any, ...],
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any],
        named_args: dict[str, Any],
        init_methods: list[Callable[[Any], None]],
    ) -> _RegisteredType[InstanceT]:
        r_type = _RegisteredType(cls, params, strategy, args, named_args, init_methods)
        self._types[hash(super_params)] = r_type
        return r_type

    def __repr__(self) -> str:
        return f"<RegisteredTypeBag {self._cls}: [{self._match_all}], [{len(self._types)}]>"


class _InitMethodMeta:
    pass


def init_method(
    func: Callable[Concatenate[InstanceT, FuncP], None]
) -> Callable[Concatenate[InstanceT, FuncP], None]:
    meta.set(func, _InitMethodMeta())
    return func


class _InjectionParamsMeta:
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
        self.kwargs = named_args or {}
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
        _cls, _ = Injection._get_generic_params(cls)
        meta.set(
            _cls,
            _InjectionParamsMeta(strategy, args, named_args, init_methods, match_all),
        )
        (cache or __user_cache__).add(InjectionSymbol, cls)
        return cls

    return decorator


def require(cls: type[InstanceT]) -> Callable[[Callable], _InjectionHook[InstanceT]]:
    def decorator(func: Callable) -> _InjectionHook[InstanceT]:
        _cls, params = Injection._get_generic_params(cls)
        return _InjectionHook(_cls, params)

    return decorator


class ArgResolverOptions:
    def __init__(
        self,
        injection: Injection,
        caller: Callable,
        name: str,
        cls: type[Any],
        generic_params: tuple[Any, ...],
        nullable: bool,
        default_set: bool,
        default: Any | None,
        immediate: bool,
    ) -> None:
        self.injection = injection
        self.caller = caller
        self.name = name
        self.cls = cls
        self.generic_params = generic_params
        self.nullable = nullable
        self.default_set = default_set
        self.default = default
        self.immediate = immediate


class ArgumentResolver(Protocol):
    def __init__(self) -> None:
        ...

    def supports(self, options: ArgResolverOptions) -> bool:
        ...

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        ...


class _ArgResolverMeta:
    def __init__(self, priority: int) -> None:
        self.priority = priority


ArgResolverT = TypeVar("ArgResolverT", bound=ArgumentResolver)


def injection_arg_resolver(
    *, priority: int = 0, cache: Cache | None = None
) -> Callable[[type[ArgResolverT]], type[ArgResolverT]]:
    def decorator(cls: type[ArgResolverT]) -> type[ArgResolverT]:
        (cache or __user_cache__).add(ArgumentResolver, cls)
        meta.set(cls, _ArgResolverMeta(priority))
        return cls

    return decorator
