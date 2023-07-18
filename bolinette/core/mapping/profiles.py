from typing import Any, Callable, Generic, Self, TypeVar

from bolinette.core import Cache, __user_cache__
from bolinette.core.expressions import AttributeNode, ExpressionTree
from bolinette.core.mapping.sequence import (
    ForAttributeMapping,
    IgnoreAttribute,
    IncludeFromBase,
    MapFromAttribute,
    MappingFunction,
    MappingSequence,
)
from bolinette.core.types import Type

SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)


class MapFromOptions:
    def __init__(self, attr: MapFromAttribute) -> None:
        self.step = attr

    def use_type(self, cls: type[Any]) -> None:
        self.step.use_type = Type(cls)


class MappingOptions(Generic[SrcT, DestT]):
    def __init__(self, dest_expr: AttributeNode) -> None:
        self.dest_expr = dest_expr
        self.step: ForAttributeMapping | None = None

    def map_from(self, func: Callable[[SrcT], Any]) -> MapFromOptions:
        src_expr: AttributeNode = func(ExpressionTree.new())  # type: ignore
        src_attr = ExpressionTree.get_attribute_name(src_expr)
        dest_attr = ExpressionTree.get_attribute_name(self.dest_expr)
        self.step = MapFromAttribute(src_attr, dest_attr)
        return MapFromOptions(self.step)

    def ignore(self) -> None:
        attr = ExpressionTree.get_attribute_name(self.dest_expr)
        self.step = IgnoreAttribute(attr)


class SequenceBuilder(Generic[SrcT, DestT]):
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.sequence = MappingSequence(src, dest)

    def for_attr(
        self,
        func: Callable[[DestT], Any],
        options: Callable[[MappingOptions[SrcT, DestT]], MapFromOptions | None],
    ) -> Self:
        expr: AttributeNode = func(ExpressionTree.new())  # type: ignore
        opt: MappingOptions[SrcT, DestT] = MappingOptions(expr)
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
