from collections.abc import Callable, Iterable
from typing import Any, Concatenate, NotRequired, TypedDict, override

from bolinette.core.exceptions import InjectionError
from bolinette.core.injection.context import InjectionStrategy
from bolinette.core.types import Type


class RegistrationOptions[InstanceT](TypedDict):
    args: NotRequired[list[Any]]
    named_args: NotRequired[dict[str, Any]]
    before_init: NotRequired[list[Callable[Concatenate[InstanceT, ...], None]]]
    after_init: NotRequired[list[Callable[Concatenate[InstanceT, ...], None]]]


class RegisteredType[InstanceT]:
    def __init__(
        self,
        intrfc_t: Type[InstanceT],
        implmt_t: Type[Any],
        strategy: InjectionStrategy,
        options: RegistrationOptions[InstanceT],
    ) -> None:
        self.intrfc_t = intrfc_t
        self.implmt_t = implmt_t
        self.strategy = strategy
        self.options = options
        self.args = options.get("args", [])
        self.named_args = options.get("named_args", {})
        self.before_init = options.get("before_init", [])
        self.after_init = options.get("after_init", [])

    @override
    def __repr__(self) -> str:
        return f"<RegisteredType {self.intrfc_t} -> {self.implmt_t} ({self.strategy})>"

    def add_before_init(self, fn: Callable[Concatenate[InstanceT, ...], None]) -> None:
        self.before_init.append(fn)

    def add_after_init(self, fn: Callable[Concatenate[InstanceT, ...], None]) -> None:
        self.after_init.append(fn)


class RegisteredTypeBag[InstanceT]:
    def __init__(self, cls: type[InstanceT]) -> None:
        self._cls = cls
        self._match_all: RegisteredType[InstanceT] | None = None
        self._types: dict[int, RegisteredType[InstanceT]] = {}

    @property
    def match_all_type(self) -> RegisteredType[Any] | None:
        return self._match_all

    @property
    def types(self) -> Iterable[RegisteredType[Any]]:
        return self._types.values()

    def has_type(self, t: Type[InstanceT]) -> bool:
        return hash(t) in self._types

    def has_match_all(self) -> bool:
        return self._match_all is not None

    def is_registered(self, t: Type[InstanceT]) -> bool:
        return self.has_type(t) or self.has_match_all()

    def get_type(self, t: Type[InstanceT]) -> RegisteredType[InstanceT]:
        if (h := hash(t)) in self._types:
            return self._types[h]
        if self._match_all is not None:
            return RegisteredType(
                self._match_all.intrfc_t,
                t,
                self._match_all.strategy,  # pyright: ignore[reportArgumentType]
                self._match_all.options,
            )
        raise InjectionError(f"Type {self._cls} has not been registered with parameters {t.vars}")

    def set_match_all(
        self,
        intrfc_t: Type[InstanceT],
        implmt_t: Type[Any],
        strategy: InjectionStrategy,
        options: RegistrationOptions[InstanceT],
    ) -> RegisteredType[InstanceT]:
        r_type = RegisteredType(intrfc_t, implmt_t, strategy, options)
        self._match_all = r_type
        return r_type

    def add_type(
        self,
        intrfc_t: Type[InstanceT],
        implmt_t: Type[Any],
        strategy: InjectionStrategy,
        options: RegistrationOptions[InstanceT],
    ) -> RegisteredType[InstanceT]:
        r_type = RegisteredType(intrfc_t, implmt_t, strategy, options)
        self._types[hash(intrfc_t)] = r_type
        return r_type

    @override
    def __repr__(self) -> str:
        return f"<RegisteredTypeBag {self._cls}: [{self._match_all}], [{len(self._types)}]>"
