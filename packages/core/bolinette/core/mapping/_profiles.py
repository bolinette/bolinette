from collections.abc import Callable
from typing import Any, Self

from peritype import wrap_type

from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.mapping._sequence import MappingSequence
from bolinette.core.mapping._spec import FieldOverride


class MappingOptions[SrcT, DestT]:
    def __init__(self, sequence: MappingSequence[SrcT, DestT]) -> None:
        self._sequence = sequence
        self._kwargs: dict[str, Any] = {}

    def map_from(self, func: Callable[[SrcT], Any]) -> Self:
        expr: ExpressionNode = func(ExpressionTree.new(self._sequence.src_t))  # pyright: ignore[reportArgumentType]
        self._kwargs["source_expr"] = expr
        return self

    def use_type(self, annotation: Any) -> Self:
        self._kwargs["use_type"] = wrap_type(annotation)
        return self

    def ignore(self) -> Self:
        self._kwargs["ignore"] = True
        return self

    def read_only(self) -> Self:
        self._kwargs["read_only"] = True
        return self

    def allow_write(self) -> Self:
        self._kwargs["allow_write"] = True
        return self

    def default(self, factory: Callable[[], Any]) -> Self:
        self._kwargs["default_factory"] = factory
        return self

    def build(self) -> FieldOverride:
        return FieldOverride(**self._kwargs)


class SequenceBuilder[SrcT, DestT]:
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.sequence = MappingSequence(src, dest)

    def for_attr(
        self,
        func: Callable[[DestT], Any],
        options: Callable[[MappingOptions[SrcT, DestT]], Any],
    ) -> Self:
        dest_expr: ExpressionNode = func(ExpressionTree.new(self.sequence.dest_t))  # pyright: ignore[reportArgumentType]
        opt: MappingOptions[SrcT, DestT] = MappingOptions(self.sequence)
        options(opt)
        self.sequence.add_override(dest_expr, opt.build())
        return self

    def before_mapping(self, func: Callable[[SrcT, DestT], None]) -> Self:
        self.sequence.head.append(func)
        return self

    def after_mapping(self, func: Callable[[SrcT, DestT], None]) -> Self:
        self.sequence.tail.append(func)
        return self

    def include(self, src_cls: type[Any], dest_cls: type[Any]) -> Self:
        self.sequence.includes.append((wrap_type(src_cls), wrap_type(dest_cls)))
        return self


class Profile:
    def __init__(self) -> None:
        self._sequences: list[MappingSequence[Any, Any]] = []

    @property
    def sequences(self) -> list[MappingSequence[Any, Any]]:
        return [*self._sequences]

    def register[SrcT, DestT](self, src: type[SrcT], dest: type[DestT]) -> SequenceBuilder[SrcT, DestT]:
        builder = SequenceBuilder(src, dest)
        self._sequences.append(builder.sequence)
        return builder
