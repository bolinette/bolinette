from collections.abc import Callable
from typing import Any, Concatenate, Literal, override

from bolinette.core.exceptions import InjectionError
from bolinette.core.types import Type

InjectionStrategy = Literal["singleton", "scoped", "transient", "immediate"]
AddStrategy = Literal["singleton", "scoped", "transient"]


class RegisteredType[InstanceT]:
    __slots__ = ("t", "strategy", "args", "named_args", "before_init", "after_init")

    def __init__(
        self,
        t: Type[InstanceT],
        strategy: InjectionStrategy,
        args: list[Any],
        named_args: dict[str, Any],
        before_init: list[Callable[..., None]],
        after_init: list[Callable[..., None]],
    ) -> None:
        self.t = t
        self.strategy = strategy
        self.args = args
        self.named_args = named_args
        self.before_init = before_init
        self.after_init = after_init

    @override
    def __repr__(self) -> str:
        return f"<RegisteredType {self.t}: {self.strategy}>"


class RegisteredTypeBag[InstanceT]:
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
        strategy: InjectionStrategy,
        args: list[Any],
        named_args: dict[str, Any],
        before_init: list[Callable[Concatenate[InstanceT, ...], None]],
        after_init: list[Callable[Concatenate[InstanceT, ...], None]],
    ) -> RegisteredType[InstanceT]:
        r_type = RegisteredType(t, strategy, args, named_args, before_init, after_init)
        self._match_all = r_type
        return r_type

    def add_type(
        self,
        super_t: Type[InstanceT],
        t: Type[InstanceT],
        strategy: InjectionStrategy,
        args: list[Any],
        named_args: dict[str, Any],
        before_init: list[Callable[Concatenate[InstanceT, ...], None]],
        after_init: list[Callable[Concatenate[InstanceT, ...], None]],
    ) -> RegisteredType[InstanceT]:
        r_type = RegisteredType(t, strategy, args, named_args, before_init, after_init)
        self._types[hash(super_t)] = r_type
        return r_type

    @override
    def __repr__(self) -> str:
        return f"<RegisteredTypeBag {self._cls}: [{self._match_all}], [{len(self._types)}]>"
