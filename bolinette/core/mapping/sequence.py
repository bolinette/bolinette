from typing import Any, Callable, Generic, TypeVar

from typing_extensions import override

from bolinette.core.exceptions import MappingError
from bolinette.core.types import Type

SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)


class ForAttributeMapping:
    __slots__ = "dest_attr"

    def __init__(self, dest_attr: str) -> None:
        self.dest_attr = dest_attr


class MapFromAttribute(ForAttributeMapping):
    __slots__ = ("src_attr", "use_type")

    def __init__(self, src_attr: str, dest_attr: str) -> None:
        ForAttributeMapping.__init__(self, dest_attr)
        self.src_attr = src_attr
        self.use_type: Type[Any] | None = None


class IgnoreAttribute(ForAttributeMapping):
    __slots__ = "func"

    def __init__(self, dest_attr: str) -> None:
        ForAttributeMapping.__init__(self, dest_attr)


class MappingFunction(Generic[SrcT, DestT]):
    __slots__ = "func"

    def __init__(self, func: Callable[[SrcT, DestT], None]) -> None:
        self.func = func


class IncludeFromBase(Generic[SrcT, DestT]):
    __slots__ = ("src_t", "dest_t")

    def __init__(self, src_t: Type[SrcT], dest_t: Type[DestT]) -> None:
        self.src_t = src_t
        self.dest_t = dest_t


class MappingSequence(Generic[SrcT, DestT]):
    __slots__ = ("src_t", "dest_t", "head", "for_attrs", "tail", "includes")

    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.src_t = Type(src)
        self.dest_t = Type(dest)
        self.head: list[MappingFunction[SrcT, DestT]] = []
        self.for_attrs: dict[str, ForAttributeMapping] = {}
        self.tail: list[MappingFunction[SrcT, DestT]] = []
        self.includes: list[IncludeFromBase[Any, Any]] = []

    @staticmethod
    def get_hash(
        src_t: Type[Any],
        dest_t: Type[Any],
    ) -> int:
        return hash((src_t, dest_t))

    @override
    def __hash__(self) -> int:
        return MappingSequence.get_hash(self.src_t, self.dest_t)

    def add_head_func(self, func: MappingFunction[SrcT, DestT]) -> None:
        self.head.append(func)

    def add_for_attr(self, for_attr: ForAttributeMapping) -> None:
        self.for_attrs[for_attr.dest_attr] = for_attr

    def add_tail_func(self, func: MappingFunction[SrcT, DestT]) -> None:
        self.tail.append(func)

    def add_include(self, include: IncludeFromBase[Any, Any]) -> None:
        self.includes.append(include)

    def complete(self, completed: "dict[int, MappingSequence[Any, Any]]") -> None:
        head: list[MappingFunction[Any, Any]] = []
        for_attrs: dict[str, ForAttributeMapping] = {}
        tail: list[MappingFunction[Any, Any]] = []
        for include in self.includes:
            if (h := MappingSequence.get_hash(include.src_t, include.dest_t)) not in completed:
                raise MappingError(
                    f"Mapping ({self.src_t} -> {self.dest_t}): "
                    f"Could not find base mapping ({include.src_t} -> {include.dest_t}). "
                    "Make sure the mappings are declared in the right order."
                )
            base_seq = completed[h]
            head.extend(base_seq.head)
            for_attrs.update(base_seq.for_attrs)
            tail.extend(base_seq.tail)
        self.head = [*head, *self.head]
        self.for_attrs = {**for_attrs, **self.for_attrs}
        self.tail = [*tail, *self.tail]
