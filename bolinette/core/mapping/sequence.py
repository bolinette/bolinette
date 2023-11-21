from collections.abc import Callable
from typing import Any, override

from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.mapping.exceptions import MappingError
from bolinette.core.types import Type


class ForAttributeMapping:
    __slots__ = "dest_expr"

    def __init__(self, dest_expr: ExpressionNode) -> None:
        self.dest_expr = dest_expr


class MapFromAttribute(ForAttributeMapping):
    __slots__ = ("src_expr", "use_type")

    def __init__(self, src_expr: ExpressionNode, dest_expr: ExpressionNode) -> None:
        ForAttributeMapping.__init__(self, dest_expr)
        self.src_expr = src_expr
        self.use_type: Type[Any] | None = None


class IgnoreAttribute(ForAttributeMapping):
    __slots__ = "func"

    def __init__(self, dest_expr: ExpressionNode) -> None:
        ForAttributeMapping.__init__(self, dest_expr)


class MappingFunction[SrcT, DestT]:
    __slots__ = "func"

    def __init__(self, func: Callable[[SrcT, DestT], None]) -> None:
        self.func = func


class IncludeFromBase[SrcT, DestT]:
    __slots__ = ("src_t", "dest_t")

    def __init__(self, src_t: Type[SrcT], dest_t: Type[DestT]) -> None:
        self.src_t = src_t
        self.dest_t = dest_t


class MappingSequence[SrcT, DestT]:
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
        ExpressionTree.ensure_attribute_chain(for_attr.dest_expr, max_depth=1)
        attr_name = ExpressionTree.get_attribute(for_attr.dest_expr)
        self.for_attrs[attr_name] = for_attr

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
