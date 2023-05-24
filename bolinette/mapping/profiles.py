from typing import Any, Callable, Generic, Self, TypeVar

from bolinette import Cache, __user_cache__
from bolinette.expressions import AttributeNode, ExpressionTree
from bolinette.mapping.sequence import (
    ForAttributeMapping,
    IgnoreAttribute,
    IncludeFromBase,
    MapFromAttribute,
    MappingFunction,
    MappingSequence,
)
from bolinette.types import Type

SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)


class MappingOptions(Generic[SrcT, DestT]):
    def __init__(self, dest_expr: AttributeNode, sequence: MappingSequence[SrcT, DestT]) -> None:
        self.dest_expr = dest_expr
        self.sequence = sequence
        self.step: ForAttributeMapping | None = None

    def map_from(self, func: Callable[[SrcT], Any]) -> None:
        src_expr: AttributeNode = func(ExpressionTree.new())  # type: ignore
        src_attr = ExpressionTree.get_attribute_name(src_expr)
        dest_attr = ExpressionTree.get_attribute_name(self.dest_expr)
        self.step = MapFromAttribute(src_attr, dest_attr)

    def ignore(self) -> None:
        attr = ExpressionTree.get_attribute_name(self.dest_expr)
        self.step = IgnoreAttribute(attr)


class SequenceBuilder(Generic[SrcT, DestT]):
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.sequence = MappingSequence(src, dest)

    def for_attr(
        self,
        func: Callable[[DestT], Any],
        options: Callable[[MappingOptions[SrcT, DestT]], None],
    ) -> Self:
        expr: AttributeNode = func(ExpressionTree.new())  # type: ignore
        opt = MappingOptions(expr, self.sequence)
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
        self._sequences: list[MappingSequence] = []

    @property
    def sequences(self) -> list[MappingSequence]:
        return [*self._sequences]

    def register(self, src: type[SrcT], dest: type[DestT]) -> SequenceBuilder[SrcT, DestT]:
        builder = SequenceBuilder(src, dest)
        self._sequences.append(builder.sequence)
        return builder


ProfileT = TypeVar("ProfileT", bound=Profile)


def mapping(*, cache: Cache | None = None) -> Callable[[type[ProfileT]], type[ProfileT]]:
    def decorator(cls: type[ProfileT]) -> type[ProfileT]:
        (cache or __user_cache__).add(Profile, cls)
        return cls

    return decorator
