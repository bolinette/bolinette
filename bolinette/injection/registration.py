from typing import Any, Callable, Generic, Literal, TypeVar

from bolinette.exceptions import InjectionError
from bolinette.types import Type

InstanceT = TypeVar("InstanceT")


class RegisteredType(Generic[InstanceT]):
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


class RegisteredTypeBag(Generic[InstanceT]):
    __slots__ = ("_cls", "_match_all", "_types")

    def __init__(self, cls: type[InstanceT]) -> None:
        self._cls = cls
        self._match_all: RegisteredType[InstanceT] | None = None
        self._types: dict[int, RegisteredType[InstanceT]] = {}

    def has_type(self, t: Type[InstanceT]) -> bool:
        return hash(t) in self._types

    def has_match_all(self) -> bool:
        return self._match_all is not None

    def is_registered(self, t: Type[InstanceT]) -> bool:
        return self.has_type(t) or self.has_match_all()

    def get_type(self, t: Type[Any]) -> RegisteredType[InstanceT]:
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
    ) -> RegisteredType[InstanceT]:
        r_type = RegisteredType(t, strategy, args, named_args, init_methods)
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
    ) -> RegisteredType[InstanceT]:
        r_type = RegisteredType(t, strategy, args, named_args, init_methods)
        self._types[hash(super_t)] = r_type
        return r_type

    def __repr__(self) -> str:
        return f"<RegisteredTypeBag {self._cls}: [{self._match_all}], [{len(self._types)}]>"
