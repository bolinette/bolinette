import inspect
from collections.abc import Callable, Collection
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
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

from typing_extensions import override

from bolinette.core import Cache, GenericMeta, meta
from bolinette.core.exceptions import InjectionError
from bolinette.core.injection.context import InjectionContext
from bolinette.core.injection.decorators import (
    InitMethodMeta,
    InjectionParamsMeta,
    InjectionSymbol,
)
from bolinette.core.injection.hook import InjectionHook, InjectionProxy
from bolinette.core.injection.registration import (
    InjectionStrategy,
    RegisteredType,
    RegisteredTypeBag,
)
from bolinette.core.injection.resolver import (
    ArgResolverMeta,
    ArgResolverOptions,
    ArgumentResolver,
    DefaultArgResolver,
)
from bolinette.core.types import Type, TypeVarLookup
from bolinette.core.utils import OrderedSet

FuncP = ParamSpec("FuncP")
FuncT = TypeVar("FuncT")
InstanceT = TypeVar("InstanceT")


class Injection:
    __slots__ = ("_cache", "_global_ctx", "_types", "_arg_resolvers")
    _ADD_INSTANCE_STRATEGIES = ("singleton",)
    _REQUIREABLE_STRATEGIES = ("singleton", "transcient")

    def __init__(
        self,
        cache: Cache,
        global_ctx: InjectionContext | None = None,
        types: "dict[type[Any], RegisteredTypeBag[Any]] | None" = None,
    ) -> None:
        self._arg_resolvers: list[ArgumentResolver] = []
        self._cache = cache
        self._global_ctx = global_ctx or InjectionContext()
        self._types = types if types is not None else self._pickup_types(cache)
        self._add_type_instance(Type(Cache), Type(Cache), False, "singleton", [], {}, [], [], cache, safe=True)
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
        for cls in cache.get(InjectionSymbol, hint=type):
            t = Type(cls)
            if t.cls not in types:
                types[t.cls] = RegisteredTypeBag(t.cls)
            type_bag = types[t.cls]
            _meta = meta.get(t.cls, InjectionParamsMeta)
            if _meta.match_all:
                type_bag.set_match_all(
                    t,
                    _meta.strategy,  # type: ignore
                    _meta.args,
                    _meta.named_args,
                    _meta.before_init,
                    _meta.after_init,
                )
            else:
                type_bag.add_type(
                    t,
                    t,
                    _meta.strategy,  # type: ignore
                    _meta.args,
                    _meta.named_args,
                    _meta.before_init,
                    _meta.after_init,
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
            resolvers.append(self.instanciate(cls, additional_resolvers=[DefaultArgResolver()]))

        return [*resolvers, DefaultArgResolver()]

    def __has_instance__(self, r_type: "RegisteredType[Any]") -> bool:
        return r_type.strategy == "singleton" and self._global_ctx.has_instance(r_type.t)

    def __get_instance__(self, r_type: "RegisteredType[InstanceT]") -> InstanceT:
        return self._global_ctx.get_instance(r_type.t)

    def __set_instance__(self, r_type: "RegisteredType[InstanceT]", instance: InstanceT) -> None:
        if r_type.strategy == "singleton":
            self._global_ctx.set_instance(r_type.t, instance)

    def _resolve_args(
        self,
        func: Callable[..., Any],
        func_type_vars: tuple[Any, ...] | None,
        strategy: InjectionStrategy,
        vars_lookup: TypeVarLookup[Any] | None,
        immediate: bool,
        circular_guard: OrderedSet[Any],
        args: list[Any],
        named_args: dict[str, Any],
        additional_resolvers: list[ArgumentResolver],
    ) -> dict[str, Any]:
        if func in circular_guard:
            call_chain = " -> ".join(str(f) for f in circular_guard) + f" -> {func}"
            raise InjectionError(f"A circular call has been detected: {call_chain}", cls=circular_guard[0])
        circular_guard.add(func)

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

            hint: type = hints[p_name]

            if get_origin(hint) in (UnionType, Union):
                type_args = get_args(hint)
                nullable = type(None) in type_args
                if not nullable or (nullable and len(type_args) >= 3):
                    raise InjectionError("Type unions are not allowed", func=func, param=p_name)
                hint = next(filter(lambda t: t is not NoneType, type_args))

            hint_t = Type(hint, lookup=vars_lookup)

            for resolver in [*additional_resolvers, *self._arg_resolvers]:
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
                    circular_guard,
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

    def _run_init_recursive(
        self,
        cls: type[InstanceT],
        instance: InstanceT,
        vars_lookup: TypeVarLookup[InstanceT] | None,
        circular_guard: OrderedSet[Any] | None,
    ) -> None:
        for base in cls.__bases__:
            self._run_init_recursive(base, instance, vars_lookup, circular_guard)
        for _, attr in vars(cls).items():
            if meta.has(attr, InitMethodMeta):
                self.call(attr, args=[instance], vars_lookup=vars_lookup, circular_guard=circular_guard)

    def _run_init_methods(
        self,
        r_type: "RegisteredType[InstanceT]",
        instance: InstanceT,
        vars_lookup: TypeVarLookup[InstanceT] | None,
        circular_guard: OrderedSet[Any],
    ):
        for method in r_type.before_init:
            self.call(method, args=[instance], circular_guard=circular_guard)
        self._run_init_recursive(r_type.t.cls, instance, vars_lookup, circular_guard)
        for method in r_type.after_init:
            self.call(method, args=[instance], circular_guard=circular_guard)

    def __instanciate__(
        self,
        r_type: "RegisteredType[InstanceT]",
        t: Type[InstanceT],
        circular_guard: OrderedSet[Any],
    ) -> InstanceT:
        vars_lookup = TypeVarLookup(t)
        func_args = self._resolve_args(
            r_type.t.cls,
            t.vars,
            r_type.strategy,  # type: ignore
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
        additional_resolvers: list[ArgumentResolver] | None = None,
        circular_guard: OrderedSet[Any] | None = None,
    ) -> FuncT:
        func_args = self._resolve_args(
            func,
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

    def instanciate(
        self,
        cls: type[InstanceT],
        *,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        additional_resolvers: list[ArgumentResolver] | None = None,
    ) -> InstanceT:
        t = Type(cls)
        init_args = self._resolve_args(
            cls,
            t.vars,
            "immediate",
            None,
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
        self._run_init_recursive(cls, instance, None, None)
        return instance

    def _add_type_instance(
        self,
        super_t: Type[InstanceT],
        t: Type[InstanceT],
        match_all: bool,
        strategy: InjectionStrategy,
        args: list[Any],
        named_args: dict[str, Any],
        before_init: list[Callable[[Any], None]],
        after_init: list[Callable[[Any], None]],
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
    def add(
        self,
        cls: type[InstanceT],
        strategy: InjectionStrategy,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        before_init: list[Callable[[InstanceT], None]] | None = None,
        after_init: list[Callable[[InstanceT], None]] | None = None,
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
        strategy: InjectionStrategy,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        before_init: list[Callable[[InstanceT], None]] | None = None,
        after_init: list[Callable[[InstanceT], None]] | None = None,
        match_all: bool = False,
        super_cls: type[InstanceT] | None = None,
    ) -> None:
        pass

    def add(
        self,
        cls: type[InstanceT],
        strategy: InjectionStrategy,
        args: list[Any] | None = None,
        named_args: dict[str, Any] | None = None,
        instance: InstanceT | None = None,
        before_init: list[Callable[[InstanceT], None]] | None = None,
        after_init: list[Callable[[InstanceT], None]] | None = None,
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
        if instanciate:
            return self.require(t.cls)  # type: ignore
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
        if self.__has_instance__(r_type):
            return self.__get_instance__(r_type)
        return self.__instanciate__(r_type, t, OrderedSet())

    def get_scoped_session(self) -> "ScopedInjection":
        return ScopedInjection(self._cache, self._global_ctx, InjectionContext(), self._types)


class ScopedInjection(Injection):
    __slots__ = "_scoped_ctx"

    _ADD_INSTANCE_STRATEGIES = ("singleton", "scoped")
    _REQUIREABLE_STRATEGIES = ("singleton", "scoped", "transcient")

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
    def __get_instance__(self, r_type: "RegisteredType[InstanceT]") -> InstanceT:
        if self._scoped_ctx.has_instance(r_type.t):
            return self._scoped_ctx.get_instance(r_type.t)
        return self._global_ctx.get_instance(r_type.t)

    @override
    def __set_instance__(self, r_type: "RegisteredType[InstanceT]", instance: InstanceT) -> None:
        strategy = r_type.strategy
        if strategy == "scoped":
            self._scoped_ctx.set_instance(r_type.t, instance)
        if strategy == "singleton":
            self._global_ctx.set_instance(r_type.t, instance)

    @override
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
            resolvers.append(self.instanciate(cls, additional_resolvers=[DefaultArgResolver()]))

        return [*resolvers, DefaultArgResolver()]

    @override
    def call(
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
            func,
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


class _GenericOrigin(Protocol):
    __parameters__: tuple[TypeVar, ...]


def _format_list(collection: Collection[Any], *, sep: str = ", ", final_sep: str | None = None) -> str:
    """TODO: move this into StringUtils and rework import flow"""
    formatted: list[str] = []
    cnt = len(collection)
    for i, e in enumerate(collection):
        formatted.append(str(e))
        if i != cnt - 1:
            if i == cnt - 2 and final_sep:
                formatted.append(final_sep)
            else:
                formatted.append(sep)
    return "".join(formatted)
