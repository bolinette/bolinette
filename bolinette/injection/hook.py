from typing import Any, Generic, TypeVar

from bolinette import injection, meta
from bolinette.exceptions import InjectionError
from bolinette.injection.registration import RegisteredType
from bolinette.types import Type

InstanceT = TypeVar("InstanceT")


class InjectionHook(Generic[InstanceT]):
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


class InjectionProxy:
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
        if inject._has_instance(self.r_type):
            obj = inject._get_instance(self.r_type)
        else:
            obj = inject.__instanciate__(self.r_type, self.t, set())
        setattr(instance, self.name, obj)
        return obj
