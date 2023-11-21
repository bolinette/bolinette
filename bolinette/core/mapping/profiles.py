from collections.abc import Callable
from typing import Any, Self

from bolinette.core import Cache, __user_cache__
from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.mapping.sequence import (
    ForAttributeMapping,
    IgnoreAttribute,
    IncludeFromBase,
    MapFromAttribute,
    MappingFunction,
    MappingSequence,
)
from bolinette.core.types import Type


class MapFromOptions:
    def __init__(self, attr: MapFromAttribute) -> None:
        self.step = attr

    def use_type(self, cls: type[Any]) -> None:
        self.step.use_type = Type(cls)


class MappingOptions[SrcT, DestT]:
    def __init__(self, sequence: MappingSequence[SrcT, DestT], dest_expr: ExpressionNode) -> None:
        self.sequence = sequence
        self.dest_expr = dest_expr
        self.step: ForAttributeMapping | None = None

    def map_from(self, func: Callable[[SrcT], Any]) -> MapFromOptions:
        src_expr: ExpressionNode = func(ExpressionTree.new(self.sequence.src_t))  # pyright: ignore
        self.step = MapFromAttribute(src_expr, self.dest_expr)
        return MapFromOptions(self.step)

    def ignore(self) -> None:
        self.step = IgnoreAttribute(self.dest_expr)


class SequenceBuilder[SrcT, DestT]:
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.sequence = MappingSequence(src, dest)

    def for_attr(
        self,
        func: Callable[[DestT], Any],
        options: Callable[[MappingOptions[SrcT, DestT]], MapFromOptions | None],
    ) -> Self:
        expr: ExpressionNode = func(ExpressionTree.new(self.sequence.dest_t))  # pyright: ignore
        opt: MappingOptions[SrcT, DestT] = MappingOptions(self.sequence, expr)
        options(opt)
        if opt.step is not None:
            self.sequence.add_for_attr(opt.step)
        return self

    def before_mapping(
        self,
        func: Callable[[SrcT, DestT], None],
    ) -> Self:
        step = MappingFunction(func)
        self.sequence.add_head_func(step)
        return self

    def after_mapping(
        self,
        func: Callable[[SrcT, DestT], None],
    ) -> Self:
        step = MappingFunction(func)
        self.sequence.add_tail_func(step)
        return self

    def include(self, src_cls: type[Any], dest_cls: type[Any]) -> Self:
        self.sequence.add_include(IncludeFromBase(Type(src_cls), Type(dest_cls)))
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


def mapping[ProfileT: Profile](*, cache: Cache | None = None) -> Callable[[type[ProfileT]], type[ProfileT]]:
    def decorator(cls: type[ProfileT]) -> type[ProfileT]:
        (cache or __user_cache__).add(Profile, cls)
        return cls

    return decorator
