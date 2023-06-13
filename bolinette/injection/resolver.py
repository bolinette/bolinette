from typing import Any, Callable, Literal, Protocol, TypeVar

from bolinette import Cache, __user_cache__, injection, meta
from bolinette.exceptions import InjectionError
from bolinette.injection.hook import InjectionHook
from bolinette.types import Type


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
        "circular_guard",
    )

    def __init__(
        self,
        injection: "injection.Injection",
        caller: Callable,
        caller_type_vars: tuple[Any, ...] | None,
        caller_strategy: Literal["singleton", "scoped", "transcient"],
        name: str,
        t: Type[Any],
        nullable: bool,
        default_set: bool,
        default: Any | None,
        immediate: bool,
        circular_guard: set[Any],
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
        self.circular_guard = circular_guard


class ArgumentResolver(Protocol):
    def supports(self, options: ArgResolverOptions) -> bool:
        ...

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        ...


class ArgResolverMeta:
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
                options.injection.__instanciate__(r_type, options.t, options.circular_guard),
            )
        return (options.name, InjectionHook(options.t))
