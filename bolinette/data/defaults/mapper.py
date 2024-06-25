from typing import Any, override

from sqlalchemy.orm import Mapped

from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping.exceptions import MappingError
from bolinette.core.mapping.mapper import MappingRunner, TypeMapper
from bolinette.core.types import Type


class OrmColumnTypeMapper(TypeMapper[Mapped[Any]]):
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[Any],
        src: SrcT,
        dest: Any | None,
        exc_grp: list[MappingError] | None,
    ) -> Any:
        return self.runner.map(src_expr, src_t, dest_expr, Type(dest_t.vars[0]), src, dest, exc_grp)
