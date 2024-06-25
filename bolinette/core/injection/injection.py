from collections.abc import Callable, Iterable
from types import TracebackType
from typing import Any, Concatenate, Literal, Protocol, Self, TypedDict, overload, override, runtime_checkable

from bolinette.core import Cache, GenericMeta, __user_cache__, meta
from bolinette.core.exceptions import InjectionError
from bolinette.core.injection.context import InjectionContext
from bolinette.core.injection.decorators import (
    InitMethodMeta,
    InjectionInitFuncMeta,
    InjectionParamsMeta,
    InjectionSymbol,
)
from bolinette.core.injection.hook import InjectionHook, InjectionProxy
from bolinette.core.injection.registration import AddStrategy, InjectionStrategy, RegisteredType, RegisteredTypeBag
from bolinette.core.injection.resolver import ArgResolverMeta, ArgResolverOptions, ArgumentResolver, DefaultArgResolver
from bolinette.core.types import Function, Type, TypeVarLookup
from bolinette.core.utils import OrderedSet
from bolinette.core.utils.strings import StringUtils


class Injection:
    __slots__: list[str] = ["cache", "_global_ctx", "_types", "_default_resolver", "_arg_resolvers", "_callbacks"]
    _ADD_INSTANCE_STRATEGIES = ("singleton",)
    _REQUIREABLE_STRATEGIES = ("singleton", "transient")

    def __init__(
        self,
        cache: Cache,
        global_ctx: InjectionContext | None = None,
        types: "dict[type[Any], RegisteredTypeBag[Any]] | None" = None,
    ) -> None:
        self.cache = cache
        self._callbacks: Iterable[InjectionCallback] = []
        self._global_ctx = global_ctx or InjectionContext()
        self._types = types if types is not None else self._pickup_types(cache)
        self._arg_resolvers: list[ArgumentResolver] = []
        self._default_resolver: ArgumentResolver = DefaultArgResolver()
        self._add_type_instance(Type(Cache), Type(Cache), False, "singleton", [], {}, [], [], cache, safe=True)
        self._callbacks = self._pickup_callbacks()
        self._add_type_instance(Type(Injection), Type(Injection), False, "singleton", [], {}, [], [], self, safe=True)
        self._arg_resolvers = self._pickup_resolvers(cache)

    @property
    def registered_types(self):
        return dict(self._types)

    @staticmethod
    def _pickup_types(cache: Cache) -> "dict[type[Any], RegisteredTypeBag[Any]]":
        if InjectionSymbol not in cache:
            return {}
        types: dict[type[Any], RegisteredTypeBag[Any]] = {}
        for cls in cache.get(InjectionSymbol, hint=type[Any]):
            t = Type(cls)
            if t.cls not in types:
                types[t.cls] = RegisteredTypeBag(t.cls)
            type_bag = types[t.cls]
            inject_meta: InjectionParamsMeta = meta.get(t.cls, InjectionParamsMeta)

            if meta.has(t.cls, InjectionInitFuncMeta):
                func_meta: InjectionInitFuncMeta[Any] = meta.get(t.cls, InjectionInitFuncMeta)
                before_init = func_meta.before_init
                after_init = func_meta.after_init
            else:
                before_init = []
                after_init = []

            if inject_meta.match_all:
                type_bag.set_match_all(
                    t,
                    inject_meta.strategy,  # pyright: ignore[reportArgumentType]
                    inject_meta.args,
                    inject_meta.named_args,
                    before_init,
                    after_init,
                )
            else:
                type_bag.add_type(
                    t,
                    t,
                    inject_meta.strategy,  # pyright: ignore[reportArgumentType]
                    inject_meta.args,
                    inject_meta.named_args,
                    before_init,
                    after_init,
                )
        return types

    def _pickup_resolvers(self, cache: Cache) -> "list[ArgumentResolver]":
        resolver_scoped: dict[type, bool] = {}
        resolver_priority: dict[type, int] = {}
        resolver_types: list[type[ArgumentResolver]] = []

        for t in cache.get(ArgumentResolver, hint=type[ArgumentResolver], raises=False):
            _meta = meta.get(t, ArgResolverMeta)
            resolver_priority[t] = _meta.priority
            resolver_scoped[t] = _meta.scoped
            resolver_types.append(t)
        resolver_types = sorted(resolver_types, key=lambda t: resolver_priority[t])

        resolvers: list[ArgumentResolver] = []
        for cls in resolver_types:
            if resolver_scoped[cls]:
                continue
            resolvers.append(self.instantiate(cls))

        return [*resolvers]

    def _pickup_callbacks(self) -> "Iterable[InjectionCallback]":
        return [
            self.instantiate(t) for t in self.cache.get(InjectionCallback, hint=type[InjectionCallback], raises=False)
        ]

    def _notify_callbacks(self, event: "InjectionEvent") -> None:
        for callback in self._callbacks:
            callback(event)

    def __has_instance__(self, r_type: RegisteredType[Any]) -> bool:
        return r_type.strategy == "singleton" and self._global_ctx.has_instance(r_type.t)

    def __get_instance__[InstanceT](self, r_type: RegisteredType[InstanceT]) -> InstanceT:
        return self._global_ctx.get_instance(r_type.t)

    def __set_instance__[InstanceT](self, r_type: RegisteredType[InstanceT], instance: InstanceT) -> None:
        if r_type.strategy == "singleton":
            self._global_ctx.set_instance(r_type.t, instance)

    def _resolve_args(
        self,
        obj: Type[Any] | Function[..., Any],
        type_vars: tuple[Any, ...] | None,
        strategy: InjectionStrategy,
        vars_lookup: TypeVarLookup[Any] | None,
        immediate: bool,
        circular_guard: OrderedSet[Any],
        args: list[Any],
        named_args: dict[str, Any],
        additional_resolvers: list[ArgumentResolver],
    ) -> dict[str, Any]:
        if obj in circular_guard:
            call_chain = " -> ".join(str(f) for f in circular_guard) + f" -> {obj}"
            raise InjectionError(f"A circular call has been detected: {call_chain}", cls=circular_guard[0])
        circular_guard.add(obj)

        try:
            if isinstance(obj, Function):
                annotations = obj.annotations(lookup=vars_lookup)
            else:
                annotations = obj.init.annotations(lookup=vars_lookup)
        except NameError as exp:
            raise InjectionError(f"Type hint '{exp.name}' could not be resolved", func=obj) from exp
        func_params = obj.parameters()

        if any((n, p) for n, p in func_params.items() if p.kind in (p.POSITIONAL_ONLY, p.VAR_POSITIONAL)):
            raise InjectionError(
                "Positional only parameters and positional wildcards are not allowed",
                func=obj,
            )

        f_args: dict[str, Any] = {}
        _args = [*args]
        _named_args = {**named_args}

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

            if p_name not in annotations:
                if default_set:
                    f_args[p_name] = default
                    continue
                raise InjectionError("Annotation is required", func=obj, param=p_name)

            hint: Type[Any] = annotations[p_name]

            if hint.is_union:
                raise InjectionError("Type unions are not allowed", func=obj, param=p_name)

            for resolver in [*additional_resolvers, *self._arg_resolvers, self._default_resolver]:
                options = ArgResolverOptions(
                    self,
                    obj,
                    type_vars,
                    strategy,
                    p_name,
                    hint,
                    default_set,
                    default,
                    immediate,
                    circular_guard,
                )
                if resolver.supports(options):
                    arg_name, arg_value = resolver.resolve(options)
                    f_args[arg_name] = arg_value
                    break

        if _args or _named_args:
            raise InjectionError(
                f"Expected {len(func_params)} arguments, {len(args) + len(named_args)} given",
                func=obj,
            )

        return f_args

    def __hook_proxies__(self, instance: object) -> None:
        hooks: dict[str, Type[Any]] = {}
        cls = type(instance)
        cls_attrs: dict[str, Any] = dict(vars(cls))
        attr: InjectionHook[Any] | Any
        for name, attr in cls_attrs.items():
            if isinstance(attr, InjectionHook):
                delattr(cls, name)
                hooks[name] = attr.t
        instance_attrs: dict[str, Any] = dict(vars(instance))
        for name, attr in instance_attrs.items():
            if isinstance(attr, InjectionHook):
                delattr(instance, name)
                hooks[name] = attr.t
        for name, t in hooks.items():
            r_type = self._types[t.cls].get_type(t)
            setattr(cls, name, InjectionProxy(name, r_type, t))

    def _run_init_recursive[InstanceT](
        self,
        cls: type[InstanceT],
        instance: InstanceT,
        vars_lookup: TypeVarLookup[InstanceT] | None,
        circular_guard: OrderedSet[Any] | None,
        init_meth_guard: set[Callable[..., Any]],
    ) -> None:
        for base in cls.__bases__:
            if base is object:
                continue
            self._run_init_recursive(base, instance, vars_lookup, circular_guard, init_meth_guard)
        for _, attr in vars(cls).items():
            if meta.has(attr, InitMethodMeta) and attr not in init_meth_guard:
                self.call(attr, args=[instance], vars_lookup=vars_lookup, circular_guard=circular_guard)
                init_meth_guard.add(attr)

    def _run_init_methods[InstanceT](
        self,
        r_type: RegisteredType[InstanceT],
        instance: InstanceT,
        vars_lookup: TypeVarLookup[InstanceT] | None,
        circular_guard: OrderedSet[Any],
    ):
        for method in r_type.before_init:
            self.call(method, args=[instance], circular_guard=circular_guard)
        self._run_init_recursive(r_type.t.cls, instance, vars_lookup, circular_guard, set())
        for method in r_type.after_init:
            self.call(method, args=[instance], circular_guard=circular_guard)

    def __instantiate__[InstanceT](
        self,
        r_type: RegisteredType[InstanceT],
        t: Type[InstanceT],
        circular_guard: OrderedSet[Any],
    ) -> InstanceT:
        vars_lookup = TypeVarLookup(t)
        func_args = self._resolve_args(
            r_type.t,
            t.vars,
            r_type.strategy,  # pyright: ignore
            vars_lookup,
            False,
            circular_guard,
            r_type.args,
            r_type.named_args,
            [],
        )
        instance = r_type.t.cls(**func_args)
        self.__hook_proxies__(instance)
        meta.set(instance, self, cls=Injection)
        meta.set(instance, GenericMeta(t.vars))
        self._run_init_methods(r_type, instance, vars_lookup, circular_guard)
        self.__set_instance__(r_type, instance)
        if isinstance(instance, HasEnter):
            instance.__enter__()
        self._notify_callbacks({"event": "instantiated", "strategy": r_type.strategy, "type": t, "instance": instance})  # pyright: ignore[reportArgumentType]
        return instance

    def is_registered(self, cls: type[Any] | Type[Any]) -> bool:
        if not isinstance(cls, Type):
            t = Type(cls)
        else:
            t = cls
        return t.cls in self._types and self._types[t.cls].is_registered(t)

    @staticmethod
    def _wrap_function[**FuncP, FuncT](func: Callable[FuncP, FuncT]) -> Function[FuncP, FuncT]:
        if isinstance(func, Function):
            return func  # pyright: ignore[reportUnknownVariableType]
        return Function(func)

    def call[FuncT](
        self,
        func: Callable[..., FuncT],
        *,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        vars_lookup: TypeVarLookup[Any] | None = None,
        additional_resolvers: list[ArgumentResolver] | None = None,
        circular_guard: OrderedSet[Any] | None = None,
    ) -> FuncT:
        func_args = self._resolve_args(
            self._wrap_function(func),
            None,
            "singleton",
            vars_lookup,
            True,
            circular_guard or OrderedSet(),
            args or [],
            named_args or {},
            additional_resolvers or [],
        )
        return func(**func_args)

    def instantiate[InstanceT](
        self,
        cls: type[InstanceT],
        *,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        additional_resolvers: list[ArgumentResolver] | None = None,
    ) -> InstanceT:
        t = Type(cls)
        vars_lookup = TypeVarLookup(t)
        init_args = self._resolve_args(
            t,
            t.vars,
            "immediate",
            vars_lookup,
            True,
            OrderedSet(),
            args or [],
            named_args or {},
            additional_resolvers or [],
        )
        instance = cls(**init_args)
        self.__hook_proxies__(instance)
        meta.set(instance, self, cls=Injection)
        meta.set(instance, GenericMeta(t.vars))
        self._run_init_recursive(cls, instance, vars_lookup, None, set())
        if isinstance(instance, HasEnter):
            instance.__enter__()
        return instance

    def _add_type_instance[InstanceT](
        self,
        super_t: Type[InstanceT],
        t: Type[InstanceT],
        match_all: bool,
        strategy: InjectionStrategy,
        args: list[Any],
        named_args: dict[str, Any],
        before_init: list[Callable[Concatenate[InstanceT, ...], None]],
        after_init: list[Callable[Concatenate[InstanceT, ...], None]],
        instance: InstanceT | None,
        *,
        safe: bool = False,
    ) -> None:
        if super_t.cls not in self._types:
            self._types[super_t.cls] = RegisteredTypeBag(super_t)
        type_bag = self._types[super_t.cls]
        r_type: RegisteredType[InstanceT] | None = None
        if match_all:
            if not safe or not type_bag.has_match_all():
                r_type = type_bag.set_match_all(t, strategy, args, named_args, before_init, after_init)
        else:
            if not safe or not type_bag.has_type(super_t):
                r_type = type_bag.add_type(super_t, t, strategy, args, named_args, before_init, after_init)
        if instance is not None:
            if r_type is None:
                r_type = self._types[t.cls].get_type(t)
            if not safe or not self.__has_instance__(r_type):
                self.__set_instance__(r_type, instance)

    @overload
    def add[InstanceT](
        self,
        cls: type[InstanceT],
        strategy: AddStrategy,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        before_init: list[Callable[Concatenate[InstanceT, ...], None]] | None = None,
        after_init: list[Callable[Concatenate[InstanceT, ...], None]] | None = None,
        match_all: bool = False,
        super_cls: type[InstanceT] | None = None,
        *,
        instantiate: Literal[True],
    ) -> InstanceT:
        pass

    @overload
    def add[InstanceT](
        self,
        cls: type[InstanceT],
        strategy: AddStrategy,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        before_init: list[Callable[Concatenate[InstanceT, ...], None]] | None = None,
        after_init: list[Callable[Concatenate[InstanceT, ...], None]] | None = None,
        match_all: bool = False,
        super_cls: type[InstanceT] | None = None,
    ) -> None:
        pass

    def add[InstanceT](
        self,
        cls: type[InstanceT],
        strategy: AddStrategy,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        before_init: list[Callable[Concatenate[InstanceT, ...], None]] | None = None,
        after_init: list[Callable[Concatenate[InstanceT, ...], None]] | None = None,
        match_all: bool = False,
        super_cls: type[InstanceT] | None = None,
        *,
        instantiate: bool = False,
    ) -> InstanceT | None:
        if super_cls is None:
            super_cls = cls
        t = Type(cls)
        if hasattr(t.cls, "__parameters__"):
            if len(t.cls.__parameters__) != len(t.vars) and not match_all:  # pyright: ignore
                raise InjectionError(
                    f"Type {t} requires {len(t.cls.__parameters__)} "  # pyright: ignore
                    f"generic parameters and {len(t.vars)} were given"
                )
        super_t: Type[InstanceT] = Type(super_cls)
        if instance is not None:
            if instantiate:
                raise InjectionError(
                    f"Cannot instantiate {t.cls} if an instance is provided",
                )
            if strategy not in self._ADD_INSTANCE_STRATEGIES:
                formatted_strategies = StringUtils.format_list(self._ADD_INSTANCE_STRATEGIES, final_sep=" or ")
                raise InjectionError(
                    f"Injection strategy for {t.cls} must be {formatted_strategies} if an instance is provided"
                )
        self._add_type_instance(
            super_t,
            t,
            match_all,
            strategy,
            args or [],
            named_args or {},
            before_init or [],
            after_init or [],
            instance,
        )
        if instantiate:
            return self.require(t.cls)
        return None

    def require[InstanceT](self, cls: type[InstanceT]) -> InstanceT:
        t = Type(cls)
        if not self.is_registered(t):
            raise InjectionError(f"Type {t} is not a registered type in the injection system")
        r_type = self._types[t.cls].get_type(t)
        if r_type.strategy not in self._REQUIREABLE_STRATEGIES:
            formatted_strategies = StringUtils.format_list(self._REQUIREABLE_STRATEGIES, final_sep=" or ")
            raise InjectionError(
                f"Injection strategy for {t} must be {formatted_strategies} to be required in this context"
            )
        if self.__has_instance__(r_type):
            return self.__get_instance__(r_type)
        return self.__instantiate__(r_type, t, OrderedSet())

    def get_scoped_session(self) -> "ScopedInjection":
        return ScopedInjection(self.cache, self._global_ctx, InjectionContext(), self._types)

    def get_async_scoped_session(self) -> "AsyncScopedSession":
        return AsyncScopedSession(self.cache, self._global_ctx, InjectionContext(), self._types)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None]) -> None:
        for instance in self._global_ctx.get_instances():
            if isinstance(instance, Injection):
                continue
            if isinstance(instance, HasExit):
                instance.__exit__(*args)


class ScopedInjection(Injection):
    __slots__: list[str] = ["_scoped_ctx"]

    _ADD_INSTANCE_STRATEGIES = ("singleton", "scoped")
    _REQUIREABLE_STRATEGIES = ("singleton", "scoped", "transient")

    def __init__(
        self,
        cache: Cache,
        global_ctx: InjectionContext,
        scoped_ctx: InjectionContext,
        types: "dict[type[Any], RegisteredTypeBag[Any]]",
    ) -> None:
        self._scoped_ctx = scoped_ctx
        super().__init__(cache, global_ctx, types)
        self._scoped_ctx.set_instance(Type(Injection), self)

    @override
    def __has_instance__(self, r_type: "RegisteredType[Any]") -> bool:
        return (r_type.strategy == "scoped" and self._scoped_ctx.has_instance(r_type.t)) or (
            r_type.strategy == "singleton" and self._global_ctx.has_instance(r_type.t)
        )

    @override
    def __get_instance__[InstanceT](self, r_type: RegisteredType[InstanceT]) -> InstanceT:
        if self._scoped_ctx.has_instance(r_type.t):
            return self._scoped_ctx.get_instance(r_type.t)
        return self._global_ctx.get_instance(r_type.t)

    @override
    def __set_instance__[InstanceT](self, r_type: RegisteredType[InstanceT], instance: InstanceT) -> None:
        strategy = r_type.strategy
        if strategy == "scoped":
            self._scoped_ctx.set_instance(r_type.t, instance)
        if strategy == "singleton":
            self._global_ctx.set_instance(r_type.t, instance)

    @override
    def _pickup_resolvers(self, cache: Cache) -> "list[ArgumentResolver]":
        resolver_priority: dict[type, int] = {}
        resolver_types: list[type[ArgumentResolver]] = []

        for t in cache.get(ArgumentResolver, hint=type[ArgumentResolver], raises=False):
            _meta = meta.get(t, ArgResolverMeta)
            resolver_priority[t] = _meta.priority
            resolver_types.append(t)
        resolver_types = sorted(resolver_types, key=lambda t: resolver_priority[t])

        resolvers: list[ArgumentResolver] = []
        for cls in resolver_types:
            resolvers.append(self.instantiate(cls))

        return [*resolvers]

    @override
    def call[FuncT](
        self,
        func: Callable[..., FuncT],
        *,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        vars_lookup: TypeVarLookup[Any] | None = None,
        additional_resolvers: list[ArgumentResolver] | None = None,
        circular_guard: OrderedSet[Any] | None = None,
    ) -> FuncT:
        func_args = self._resolve_args(
            self._wrap_function(func),
            None,
            "scoped",
            vars_lookup,
            True,
            circular_guard or OrderedSet(),
            args or [],
            named_args or {},
            additional_resolvers or [],
        )
        return func(**func_args)

    @override
    def __enter__(self) -> Self:
        return super().__enter__()
        self._notify_callbacks({"event": "session_open"})

    @override
    def __exit__(self, *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None]) -> None:
        for instance in self._scoped_ctx.get_instances():
            if isinstance(instance, Injection):
                continue
            if isinstance(instance, HasExit):
                instance.__exit__(*args)
        self._notify_callbacks({"event": "session_closed"})


class AsyncScopedSession(ScopedInjection):
    def __init__(
        self,
        cache: Cache,
        global_ctx: InjectionContext,
        scoped_ctx: InjectionContext,
        types: dict[type, RegisteredTypeBag[Any]],
    ) -> None:
        super().__init__(cache, global_ctx, scoped_ctx, types)

    async def __aenter__(self) -> Self:
        self._notify_callbacks({"event": "async_session_open"})
        return self

    async def __aexit__(
        self,
        *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None],
    ) -> None:
        for instance in self._scoped_ctx.get_instances():
            if isinstance(instance, Injection):
                continue
            if isinstance(instance, HasExit):
                instance.__exit__(*args)
            if isinstance(instance, HasAsyncExit):
                await instance.__aexit__(*args)
        self._notify_callbacks({"event": "async_session_closed"})


class InstanceEvent[T](TypedDict):
    event: Literal["instantiated"]
    type: Type[T]
    strategy: InjectionStrategy
    instance: T


class SessionOpenEvent(TypedDict):
    event: Literal["session_open"]


class SessionClosedEvent(TypedDict):
    event: Literal["session_closed"]


class AsyncSessionOpenEvent(TypedDict):
    event: Literal["async_session_open"]


class AsyncSessionClosedEvent(TypedDict):
    event: Literal["async_session_closed"]


type InjectionEvent = (
    InstanceEvent[Any] | SessionOpenEvent | SessionClosedEvent | AsyncSessionOpenEvent | AsyncSessionClosedEvent
)


class InjectionCallback(Protocol):
    def __call__(self, event: InjectionEvent) -> None: ...


def injection_callback[CallbackT: InjectionCallback](*, cache: Cache) -> Callable[[type[CallbackT]], type[CallbackT]]:
    def decorator(callback: type[CallbackT]) -> type[CallbackT]:
        (cache or __user_cache__).add(InjectionCallback, callback)
        return callback

    return decorator


@runtime_checkable
class HasEnter(Protocol):
    def __enter__(self) -> Self: ...


@runtime_checkable
class HasAsyncEnter(Protocol):
    def __aenter__(self) -> Self: ...


@runtime_checkable
class HasExit(Protocol):
    def __exit__(
        self, *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None]
    ) -> Self: ...


@runtime_checkable
class HasAsyncExit(Protocol):
    async def __aexit__(
        self, *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None]
    ) -> Self: ...
