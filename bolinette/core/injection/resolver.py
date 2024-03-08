from collections.abc import Callable
from typing import Any, Protocol

from bolinette.core import Cache, __user_cache__, injection, meta
from bolinette.core.exceptions import InjectionError
from bolinette.core.injection.hook import InjectionHook
from bolinette.core.injection.registration import InjectionStrategy
from bolinette.core.types import Function, Type
from bolinette.core.utils import OrderedSet


class ArgResolverOptions:
    __slots__ = (
        "injection",
        "caller",
        "caller_type_vars",
        "caller_strategy",
        "name",
        "t",
        "default_set",
        "default",
        "immediate",
        "circular_guard",
    )

    def __init__(
        self,
        injection: "injection.Injection",
        caller: Function[..., Any] | Type[Any],
        caller_type_vars: tuple[Any, ...] | None,
        caller_strategy: InjectionStrategy,
        name: str,
        t: Type[Any],
        default_set: bool,
        default: Any | None,
        immediate: bool,
        circular_guard: OrderedSet[Any],
    ) -> None:
        self.injection = injection
        self.caller = caller
        self.caller_type_vars = caller_type_vars
        self.caller_strategy = caller_strategy
        self.name = name
        self.t = t
        self.default_set = default_set
        self.default = default
        self.immediate = immediate
        self.circular_guard = circular_guard


class ArgumentResolver(Protocol):
    def supports(self, options: ArgResolverOptions) -> bool: ...

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]: ...


class ArgResolverMeta:
    __slots__ = ("priority", "scoped")

    def __init__(self, priority: int, scoped: bool) -> None:
        self.priority = priority
        self.scoped = scoped


def injection_arg_resolver[ArgResolverT: ArgumentResolver](
    *,
    priority: int = 0,
    scoped: bool = False,
    cache: Cache | None = None,
) -> Callable[[type[ArgResolverT]], type[ArgResolverT]]:
    def decorator(cls: type[ArgResolverT]) -> type[ArgResolverT]:
        (cache or __user_cache__).add(ArgumentResolver, cls)
        meta.set(cls, ArgResolverMeta(priority, scoped))
        return cls

    return decorator


class DefaultArgResolver:
    __slots__ = ()

    def supports(self, options: "ArgResolverOptions") -> bool:
        return True

    def resolve(self, options: "ArgResolverOptions") -> tuple[str, Any]:
        if options.t.cls is Type:
            return (options.name, Type(options.t.vars[0]))
        if options.t.cls is type:
            return (options.name, options.t.vars[0])

        if not options.injection.is_registered(options.t):
            if options.t.nullable:
                return (options.name, None)
            if options.default_set:
                return (options.name, options.default)
            raise InjectionError(
                f"Type {options.t} is not a registered type in the injection system",
                func=options.caller,
                param=options.name,
            )

        r_type = options.injection.registered_types[options.t.cls].get_type(options.t)

        if r_type.strategy == "scoped":
            if options.caller_strategy in ["singleton", "transient"]:
                raise InjectionError(
                    f"Cannot instantiate a scoped service in a {options.caller_strategy} service",
                    func=options.caller,
                    param=options.name,
                )

        if options.injection.__has_instance__(r_type):
            return (options.name, options.injection.__get_instance__(r_type))
        if options.immediate:
            return (
                options.name,
                options.injection.__instantiate__(r_type, options.t, options.circular_guard),
            )
        return (options.name, InjectionHook(options.t))
