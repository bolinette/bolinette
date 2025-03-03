from collections.abc import Callable, Iterable
from types import TracebackType
from typing import Any, Generic, Literal, Protocol, Self, TypedDict, overload, override, runtime_checkable

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.exceptions import InjectionError, UnregisteredTypeError
from bolinette.core.injection import RegistrationOptions
from bolinette.core.injection.context import InjectionContext
from bolinette.core.injection.decorators import (
    InjectionInitFuncMeta,
    InjectionParamsMeta,
    InjectionSymbol,
    PostInitMeta,
)
from bolinette.core.injection.hook import InjectionHook, InjectionProxy
from bolinette.core.injection.pool import InstancePool
from bolinette.core.injection.registration import AddStrategy, InjectionStrategy, RegisteredType, RegisteredTypeBag
from bolinette.core.injection.resolver import ArgResolverMeta, ArgResolverOptions, ArgumentResolver
from bolinette.core.types import Function, Type, TypeVarLookup
from bolinette.core.utils import OrderedSet


class Injection:
    _ADD_INSTANCE_STRATEGIES = ("singleton",)
    _REQUIREABLE_STRATEGIES = ("singleton", "transient")

    def __init__(
        self,
        cache: Cache,
        global_pool: InstancePool | None = None,
        types: "dict[type[Any], RegisteredTypeBag[Any]] | None" = None,
        resolvers: list[ArgumentResolver] | None = None,
    ) -> None:
        self.cache = cache
        self._callbacks: Iterable[InjectionCallback] = []
        self._global_pool = global_pool or InstancePool()
        self._types = types if types is not None else self._pickup_types(cache)
        self._arg_resolvers: list[ArgumentResolver] = []
        self._register_type(Type(Cache), Type(Cache), False, "singleton", {}, instance=cache, safe=True)
        self._register_type(Type(Injection), Type(Injection), False, "singleton", {}, instance=self, safe=True)
        self._arg_resolvers = self._pickup_resolvers(cache, resolvers or [])
        self._callbacks = self._pickup_callbacks()

    @property
    def registered_types(self) -> dict[type[Any], RegisteredTypeBag[Any]]:
        return dict(self._types)

    @property
    def is_scoped(self) -> bool:
        return False

    def is_registered(self, cls: type[Any] | Type[Any]) -> bool:
        if not isinstance(cls, Type):
            t = Type(cls)
        else:
            t = cls
        return t.cls in self._types and self._types[t.cls].is_registered(t)

    def get_registered_type[InstanceT](self, cls: type[InstanceT] | Type[InstanceT]) -> RegisteredTypeBag[InstanceT]:
        if not isinstance(cls, Type):
            t = Type(cls)
        else:
            t = cls
        if not self.is_registered(t):
            raise UnregisteredTypeError(str(t))
        return self._types[t.cls]

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
                    t,
                    inject_meta.strategy,  # pyright: ignore[reportArgumentType]
                    {
                        "args": inject_meta.args,
                        "named_args": inject_meta.named_args,
                        "before_init": before_init,
                        "after_init": after_init,
                    },
                )
            else:
                type_bag.add_type(
                    t,
                    t,
                    inject_meta.strategy,  # pyright: ignore[reportArgumentType]
                    {
                        "args": inject_meta.args,
                        "named_args": inject_meta.named_args,
                        "before_init": before_init,
                        "after_init": after_init,
                    },
                )
        return types

    def _pickup_resolvers(
        self,
        cache: Cache,
        parent_resolvers: list[ArgumentResolver],
        add_scoped: bool = False,
    ) -> list[ArgumentResolver]:
        existing_resolver_types = {type(r) for r in parent_resolvers}
        resolver_scoped: dict[type, bool] = {}
        resolver_priority: dict[type, int] = {}
        resolver_types: list[type[ArgumentResolver]] = []

        for cls in cache.get(ArgumentResolver, hint=type[ArgumentResolver], raises=False):
            if cls in existing_resolver_types:
                continue
            _meta = meta.get(cls, ArgResolverMeta)
            resolver_priority[cls] = _meta.priority
            resolver_scoped[cls] = _meta.scoped
            resolver_types.append(cls)
        resolver_types = sorted(resolver_types, key=lambda t: resolver_priority[t])

        resolvers: list[ArgumentResolver] = [*parent_resolvers]
        for cls in resolver_types:
            if resolver_scoped[cls] and not add_scoped:
                continue
            resolvers.append(self.instantiate(cls, additional_resolvers=resolvers))

        return resolvers

    def _pickup_callbacks(self) -> "Iterable[InjectionCallback]":
        return [
            self.instantiate(t) for t in self.cache.get(InjectionCallback, hint=type[InjectionCallback], raises=False)
        ]

    def _notify_callbacks(self, event: "InjectionEvent") -> None:
        for callback in self._callbacks:
            callback(event)

    def _has_instance(self, t: Type[Any]) -> bool:
        return self._global_pool.has_instance(t)

    def _get_instance[InstanceT](self, t: Type[InstanceT]) -> InstanceT:
        return self._global_pool.get_instance(t)

    def _set_instance[InstanceT](self, r_type: RegisteredType[InstanceT], instance: InstanceT) -> None:
        if r_type.strategy == "singleton":
            self._global_pool.set_instance(r_type.implmt_t, instance)

    def _resolve_args(
        self,
        obj: Type[Any] | Function[..., Any],
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

            if immediate:
                arg_value = self._resolve_type(
                    hint,
                    InjectionContext(obj, strategy, p_name, default_set, default),
                    circular_guard,
                    additional_resolvers,
                )
            else:
                arg_value = InjectionHook(hint, default_set, default)

            f_args[p_name] = arg_value

        if _args or _named_args:
            raise InjectionError(
                f"Expected {len(func_params)} arguments, {len(args) + len(named_args)} given",
                func=obj,
            )

        return f_args

    def _resolve_type(
        self,
        t: Type[Any],
        context: InjectionContext | None,
        circular_guard: OrderedSet[Any],
        additional_resolvers: list[ArgumentResolver],
    ) -> Any:
        if t.cls is Type:
            return Type(t.vars[0])
        if t.cls is type:
            return t.vars[0]

        if self.is_registered(t):
            return self._resolve_type_default(t, context, circular_guard, additional_resolvers)

        all_resolvers = [*additional_resolvers, *self._arg_resolvers]
        if len(all_resolvers):
            options = ArgResolverOptions(
                self,
                t,
                context,
                circular_guard,
                additional_resolvers,
            )
            for resolver in all_resolvers:
                if resolver.supports(options):
                    return resolver.resolve(options)
        if t.nullable:
            return None
        if context is not None and context.default_set:
            return context.default
        raise UnregisteredTypeError(
            str(t),
            func=context.origin if context else None,
            param=context.arg_name if context else None,
        )

    def _resolve_type_default(
        self,
        t: Type[Any],
        context: InjectionContext | None,
        circular_guard: OrderedSet[Any],
        additional_resolvers: list[ArgumentResolver],
    ) -> Any:
        r_type = self.registered_types[t.cls].get_type(t)

        if r_type.strategy == "scoped":
            if context and context.strategy in ["singleton", "transient"]:
                raise InjectionError(
                    f"Cannot instantiate a scoped service in a {context.strategy} service",
                    func=context.origin,
                    param=context.arg_name,
                )
            if not self.is_scoped:
                raise InjectionError(f"Cannot instantiate scoped service {t} from a non scoped injection context")

        if self._has_instance(r_type.implmt_t):
            return self._get_instance(r_type.implmt_t)
        return self._instantiate(r_type, circular_guard, additional_resolvers)

    def __hook_proxies__(self, t: Type[Any], strategy: InjectionStrategy, instance: object) -> None:
        hooks: dict[str, InjectionHook[Any]] = {}
        cls = type(instance)
        cls_attrs: dict[str, Any] = dict(vars(cls))
        attr: InjectionHook[Any] | Any
        for name, attr in cls_attrs.items():
            if isinstance(attr, InjectionHook):
                delattr(cls, name)
                hooks[name] = attr
        instance_attrs: dict[str, Any] = dict(vars(instance))
        for name, attr in instance_attrs.items():
            if isinstance(attr, InjectionHook):
                delattr(instance, name)
                hooks[name] = attr
        for name, hook in hooks.items():
            setattr(
                cls,
                name,
                InjectionProxy(hook.t, InjectionContext(t, strategy, name, hook.default_set, hook.default)),
            )

    def _run_init_recursive[InstanceT](
        self,
        cls: type[InstanceT],
        instance: InstanceT,
        vars_lookup: TypeVarLookup[InstanceT] | None,
        circular_guard: OrderedSet[Any] | None,
        post_init_guard: set[Callable[..., Any]],
        additional_resolvers: list[ArgumentResolver],
    ) -> None:
        for base in cls.__bases__:
            if base in (object, Generic):
                continue
            self._run_init_recursive(base, instance, vars_lookup, circular_guard, post_init_guard, additional_resolvers)
        for _, attr in vars(cls).items():
            if meta.has(attr, PostInitMeta) and attr not in post_init_guard:
                self.call(
                    attr,
                    args=[instance],
                    vars_lookup=vars_lookup,
                    additional_resolvers=additional_resolvers,
                    circular_guard=circular_guard,
                )
                post_init_guard.add(attr)

    def _run_post_inits[InstanceT](
        self,
        r_type: RegisteredType[InstanceT],
        instance: InstanceT,
        vars_lookup: TypeVarLookup[InstanceT] | None,
        circular_guard: OrderedSet[Any],
        additional_resolvers: list[ArgumentResolver],
    ):
        for method in r_type.before_init:
            self.call(method, args=[instance], circular_guard=circular_guard)
        self._run_init_recursive(
            r_type.implmt_t.cls, instance, vars_lookup, circular_guard, set(), additional_resolvers
        )
        for method in r_type.after_init:
            self.call(method, args=[instance], circular_guard=circular_guard)

    def _instantiate[InstanceT](
        self,
        r_type: RegisteredType[InstanceT],
        circular_guard: OrderedSet[Any],
        additional_resolvers: list[ArgumentResolver],
    ) -> InstanceT:
        vars_lookup = TypeVarLookup(r_type.implmt_t)
        func_args = self._resolve_args(
            r_type.implmt_t,
            r_type.strategy,  # pyright: ignore[reportArgumentType]
            vars_lookup,
            False,
            circular_guard,
            r_type.args,
            r_type.named_args,
            additional_resolvers,
        )
        instance: InstanceT = r_type.implmt_t.cls(**func_args)
        self.__hook_proxies__(
            r_type.implmt_t,
            r_type.strategy,  # pyright: ignore[reportArgumentType]
            instance,
        )
        meta.set(instance, self, cls=Injection)
        self._run_post_inits(r_type, instance, vars_lookup, circular_guard, additional_resolvers)
        self._set_instance(r_type, instance)
        if isinstance(instance, HasEnter):
            instance.__enter__()
        self._notify_callbacks(
            {
                "event": "instantiated",
                "strategy": r_type.strategy,  # pyright: ignore[reportArgumentType]
                "type": r_type.implmt_t,
                "instance": instance,
            }
        )
        return instance

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
            "immediate",
            vars_lookup,
            False,
            OrderedSet(),
            args or [],
            named_args or {},
            additional_resolvers or [],
        )
        instance = cls(**init_args)
        self.__hook_proxies__(t, "immediate", instance)
        meta.set(instance, self, cls=Injection)
        self._run_init_recursive(cls, instance, vars_lookup, None, set(), additional_resolvers or [])
        if isinstance(instance, HasEnter):
            instance.__enter__()
        return instance

    def _register_type[InstanceT](
        self,
        intrfc_t: Type[InstanceT],
        implmt_t: Type[Any],
        match_all: bool,
        strategy: AddStrategy,
        options: RegistrationOptions[InstanceT],
        *,
        instance: InstanceT | None = None,
        safe: bool = False,
    ) -> None:
        if instance is not None and strategy not in self._ADD_INSTANCE_STRATEGIES:
            raise InjectionError(
                f"Injection strategy for {intrfc_t} must be "
                f"{' or '.join(self._ADD_INSTANCE_STRATEGIES)} if an instance is provided"
            )
        if intrfc_t.cls not in self._types:
            self._types[intrfc_t.cls] = RegisteredTypeBag(intrfc_t.cls)
        type_bag = self._types[intrfc_t.cls]
        r_type: RegisteredType[InstanceT] | None = None
        if match_all:
            if not safe or not type_bag.has_match_all():
                r_type = type_bag.set_match_all(intrfc_t, implmt_t, strategy, options)
        else:
            if not safe or not type_bag.has_type(intrfc_t):
                r_type = type_bag.add_type(intrfc_t, implmt_t, strategy, options)
        if instance is not None:
            if r_type is None:
                r_type = self._types[intrfc_t.cls].get_type(implmt_t)
            if not safe or not self._has_instance(implmt_t):
                self._set_instance(r_type, instance)

    @overload
    def add_singleton[InstanceT](
        self,
        interface: type[InstanceT],
        implementation: type[object],
        /,
        *,
        options: RegistrationOptions[InstanceT] | None = None,
        instance: InstanceT | None = None,
        match_all: bool = False,
    ) -> None: ...

    @overload
    def add_singleton[InstanceT](
        self,
        implementation: type[InstanceT],
        /,
        *,
        options: RegistrationOptions[InstanceT] | None = None,
        instance: InstanceT | None = None,
        match_all: bool = False,
    ) -> None: ...

    def add_singleton(
        self,
        *args: Any,
        options: RegistrationOptions[object] | None = None,
        instance: object | None = None,
        match_all: bool = False,
    ) -> None:
        match args:
            case (implementation,):
                self._add("singleton", implementation, implementation, options or {}, instance, match_all)
            case (interface, implementation):
                self._add("singleton", interface, implementation, options or {}, instance, match_all)
            case _:
                raise TypeError()

    @overload
    def add_transient[InstanceT](
        self,
        interface: type[InstanceT],
        implementation: type[Any],
        /,
        *,
        options: RegistrationOptions[InstanceT] | None = None,
        instance: object | None = None,
        match_all: bool = False,
    ) -> None: ...

    @overload
    def add_transient[InstanceT](
        self,
        implementation: type[InstanceT],
        /,
        *,
        options: RegistrationOptions[InstanceT] | None = None,
        instance: object | None = None,
        match_all: bool = False,
    ) -> None: ...

    def add_transient(
        self,
        *args: Any,
        options: RegistrationOptions[object] | None = None,
        instance: object | None = None,
        match_all: bool = False,
    ) -> None:
        match args:
            case (implementation,):
                self._add("transient", implementation, implementation, options or {}, instance, match_all)
            case (interface, implementation):
                self._add("transient", interface, implementation, options or {}, instance, match_all)
            case _:
                raise TypeError()

    @overload
    def add_scoped[InstanceT](
        self,
        interface: type[InstanceT],
        implementation: type[object],
        /,
        *,
        options: RegistrationOptions[InstanceT] | None = None,
        instance: InstanceT | None = None,
        match_all: bool = False,
    ) -> None: ...

    @overload
    def add_scoped[InstanceT](
        self,
        implementation: type[InstanceT],
        /,
        *,
        options: RegistrationOptions[InstanceT] | None = None,
        instance: InstanceT | None = None,
        match_all: bool = False,
    ) -> None: ...

    def add_scoped(
        self,
        *args: Any,
        options: RegistrationOptions[object] | None = None,
        instance: object | None = None,
        match_all: bool = False,
    ) -> None:
        match args:
            case (implementation,):
                self._add("scoped", implementation, implementation, options or {}, instance, match_all)
            case (interface, implementation):
                self._add("scoped", interface, implementation, options or {}, instance, match_all)
            case _:
                raise TypeError()

    def _add(
        self,
        strategy: AddStrategy,
        interface: type[Any],
        implementation: type[Any],
        options: RegistrationOptions[Any],
        instance: Any | None,
        match_all: bool,
    ) -> None:
        intrfc_t = Type(interface)
        implmt_t = Type(implementation)
        self._register_type(intrfc_t, implmt_t, match_all, strategy, options, instance=instance)

    def __require__[InstanceT](self, t: Type[InstanceT], context: InjectionContext | None) -> InstanceT:
        return self._resolve_type(t, context, OrderedSet(), [])

    def require[InstanceT](self, cls: type[InstanceT]) -> InstanceT:
        return self.__require__(Type(cls), None)

    def get_scoped_session(self) -> "ScopedInjection":
        return ScopedInjection(self.cache, self._global_pool, InstancePool(), self._types, self._arg_resolvers)

    def get_async_scoped_session(self) -> "AsyncScopedSession":
        return AsyncScopedSession(self.cache, self._global_pool, InstancePool(), self._types, self._arg_resolvers)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None]) -> None:
        for instance in self._global_pool.get_instances():
            if isinstance(instance, Injection):
                continue
            if isinstance(instance, HasExit):
                instance.__exit__(*args)


class ScopedInjection(Injection):
    _ADD_INSTANCE_STRATEGIES = ("singleton", "scoped")
    _REQUIREABLE_STRATEGIES = ("singleton", "scoped", "transient")

    def __init__(
        self,
        cache: Cache,
        global_pool: InstancePool,
        scoped_pool: InstancePool,
        types: "dict[type[Any], RegisteredTypeBag[Any]]",
        resolvers: list[ArgumentResolver] | None = None,
    ) -> None:
        self._scoped_pool = scoped_pool
        super().__init__(cache, global_pool, types, resolvers)
        self._scoped_pool.set_instance(Type(Injection), self)

    @property
    @override
    def is_scoped(self) -> bool:
        return True

    @override
    def _has_instance(self, t: Type[Any]) -> bool:
        return self._scoped_pool.has_instance(t) or self._global_pool.has_instance(t)

    @override
    def _get_instance[InstanceT](self, t: Type[InstanceT]) -> InstanceT:
        if self._scoped_pool.has_instance(t):
            return self._scoped_pool.get_instance(t)
        return self._global_pool.get_instance(t)

    @override
    def _set_instance[InstanceT](self, r_type: RegisteredType[InstanceT], instance: InstanceT) -> None:
        strategy = r_type.strategy
        if strategy == "scoped":
            self._scoped_pool.set_instance(r_type.implmt_t, instance)
        if strategy == "singleton":
            self._global_pool.set_instance(r_type.implmt_t, instance)

    @override
    def _pickup_resolvers(
        self,
        cache: Cache,
        parent_resolvers: list[ArgumentResolver],
        add_scoped: bool = False,
    ) -> list[ArgumentResolver]:
        return super()._pickup_resolvers(cache, parent_resolvers, add_scoped=True)

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
        super().__enter__()
        self._notify_callbacks({"event": "session_open"})
        return self

    @override
    def __exit__(self, *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None]) -> None:
        for instance in self._scoped_pool.get_instances():
            if isinstance(instance, Injection):
                continue
            if isinstance(instance, HasExit):
                instance.__exit__(*args)
        self._notify_callbacks({"event": "session_closed"})


class AsyncScopedSession(ScopedInjection):
    def __init__(
        self,
        cache: Cache,
        global_pool: InstancePool,
        scoped_pool: InstancePool,
        types: dict[type, RegisteredTypeBag[Any]],
        resolvers: list[ArgumentResolver] | None = None,
    ) -> None:
        super().__init__(cache, global_pool, scoped_pool, types, resolvers)

    async def __aenter__(self) -> Self:
        self._notify_callbacks({"event": "async_session_open"})
        return self

    async def __aexit__(
        self,
        *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None],
    ) -> None:
        for instance in self._scoped_pool.get_instances():
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
