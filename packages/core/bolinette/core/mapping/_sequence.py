from collections.abc import Callable
from typing import Any

from peritype import TWrap, wrap_type

from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.mapping._spec import FieldOverride
from bolinette.core.mapping.exceptions import MappingConfigurationError

type MappingFunction[SrcT, DestT] = Callable[[SrcT, DestT], None]


class MappingSequence[SrcT, DestT]:
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.src_t: TWrap[SrcT] = wrap_type(src)
        self.dest_t: TWrap[DestT] = wrap_type(dest)
        self.overrides: dict[str, FieldOverride] = {}
        self.head: list[MappingFunction[SrcT, DestT]] = []
        self.tail: list[MappingFunction[SrcT, DestT]] = []
        self.includes: list[tuple[TWrap[Any], TWrap[Any]]] = []

    @staticmethod
    def get_hash(src_t: TWrap[Any], dest_t: TWrap[Any]) -> int:
        return hash((src_t, dest_t))

    def __hash__(self) -> int:
        return MappingSequence.get_hash(self.src_t, self.dest_t)

    def add_override(self, dest_expr: ExpressionNode, override: FieldOverride) -> None:

        ExpressionTree.ensure_attribute_chain(dest_expr, max_depth=1)
        self.overrides[ExpressionTree.get_attribute(dest_expr)] = override

    def complete(self, completed: "dict[int, MappingSequence[Any, Any]]") -> None:
        head: list[MappingFunction[Any, Any]] = []
        overrides: dict[str, FieldOverride] = {}
        tail: list[MappingFunction[Any, Any]] = []
        for src_t, dest_t in self.includes:
            h = MappingSequence.get_hash(src_t, dest_t)
            if h not in completed:
                raise MappingConfigurationError(
                    [f"({self.src_t} -> {self.dest_t}): missing base mapping ({src_t} -> {dest_t})"]
                )
            base = completed[h]
            head.extend(base.head)
            overrides.update(base.overrides)
            tail.extend(base.tail)
        self.head = [*head, *self.head]
        self.overrides = {**overrides, **self.overrides}
        self.tail = [*tail, *self.tail]
