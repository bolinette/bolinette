from typing import Any, override

from bolinette.core import injection, meta
from bolinette.core.exceptions import InjectionError
from bolinette.core.injection.context import InjectionContext
from bolinette.core.types import Type


class InjectionHook[InstanceT]:
    def __init__(
        self,
        t: Type[InstanceT],
        default_set: bool,
        default: Any,
    ) -> None:
        self.t = t
        self.default_set = default_set
        self.default = default

    @override
    def __getattribute__(self, __name: str) -> Any:
        if __name in ("t", "default_set", "default", "__class__"):
            return object.__getattribute__(self, __name)
        raise InjectionError(
            f"Tried accessing member '{__name}' of an injected instance inside the __init__ method. "
            "Use @init_method to process logic at instantiation."
        )

    def __get__(self, *_) -> InstanceT:
        return None  # pyright: ignore


class InjectionProxy[InstanceT]:
    def __init__(
        self,
        t: Type[InstanceT],
        context: InjectionContext,
    ) -> None:
        self.t: Type[InstanceT] = t
        self.context = context

    def __get__(self, instance: Any, _) -> Any:
        inject = meta.get(instance, injection.Injection)
        obj = inject.__require__(self.t, self.context)
        setattr(instance, self.context.arg_name, obj)
        return obj
