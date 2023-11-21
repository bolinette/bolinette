from typing import Any, override

from bolinette.core import injection, meta
from bolinette.core.exceptions import InjectionError
from bolinette.core.injection.registration import RegisteredType
from bolinette.core.types import Type
from bolinette.core.utils import OrderedSet


class InjectionHook[InstanceT]:
    __slots__ = ("t",)

    def __init__(self, t: Type[InstanceT]) -> None:
        self.t = t

    @override
    def __getattribute__(self, __name: str) -> Any:
        if __name in ("t", "__class__"):
            return object.__getattribute__(self, __name)
        raise InjectionError(
            f"Tried accessing member '{__name}' of an injected instance inside the __init__ method. "
            "Use @init_method to process logic at instantiation."
        )

    def __get__(self, *_) -> InstanceT:
        return None  # pyright: ignore


class InjectionProxy[InstanceT]:
    __slots__ = ("name", "r_type", "t")

    def __init__(
        self,
        name: str,
        r_type: RegisteredType[InstanceT],
        t: Type[InstanceT],
    ) -> None:
        self.name = name
        self.r_type = r_type
        self.t = t

    def __get__(self, instance: Any, _) -> Any:
        inject = meta.get(instance, injection.Injection)
        if inject.__has_instance__(self.r_type):
            obj = inject.__get_instance__(self.r_type)
        else:
            obj = inject.__instantiate__(self.r_type, self.t, OrderedSet())
        setattr(instance, self.name, obj)
        return obj
