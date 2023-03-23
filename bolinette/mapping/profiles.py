from typing import Any, Callable, Generic, TypeVar, Self
from abc import ABC

from bolinette import Cache, __user_cache__
from bolinette.expressions import ExpressionTree, AttributeNode
from bolinette.mapping.sequence import MappingSequence, FromSrcMappingStep, IgnoreMappingStep, FunctionMappingStep, ToDestMappingStep


SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)


class _MappingOptions(Generic[SrcT, DestT]):
    def __init__(self, dest_expr: AttributeNode) -> None:
        self.dest_expr = dest_expr
        self.step: ToDestMappingStep | None = None

    def map_from(self, func: Callable[[SrcT], Any]) -> None:
        src_expr: AttributeNode = func(ExpressionTree.new())  # type: ignore
        src_attr: str = ExpressionTree.get_attribute_name(src_expr)
        dest_attr: str = ExpressionTree.get_attribute_name(self.dest_expr)

        def mapping_func(src: SrcT, dest: DestT) -> None:
            value = ExpressionTree.get_value(src_expr, src)
            ExpressionTree.set_value(self.dest_expr, dest, value)

        self.step = FromSrcMappingStep(src_attr, dest_attr, mapping_func)

    def ignore(self) -> None:
        attr: str = ExpressionTree.get_attribute_name(self.dest_expr)
        self.step = IgnoreMappingStep(attr)


class _SequenceBuilder(Generic[SrcT, DestT]):
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.sequence = MappingSequence(src, dest)

    def for_attr(
        self,
        func: Callable[[DestT], Any],
        options: Callable[[_MappingOptions[SrcT, DestT]], None],
    ) -> Self:
        expr: AttributeNode = func(ExpressionTree.new())  # type: ignore
        opt = _MappingOptions(expr)
        options(opt)
        if opt.step is not None:
            self.sequence.add_step(opt.step)
        return self

    def before_mapping(
        self,
        func: Callable[[SrcT, DestT], None],
    ) -> Self:
        step = FunctionMappingStep(func)
        self.sequence.add_head_step(step)
        return self

    def after_mapping(
        self,
        func: Callable[[SrcT, DestT], None],
    ) -> Self:
        step = FunctionMappingStep(func)
        self.sequence.add_tail_step(step)
        return self


class Profile(ABC):
    def __init__(self) -> None:
        self._sequences: list[MappingSequence] = []

    @property
    def sequences(self) -> list[MappingSequence]:
        return [*self._sequences]

    def register(self, src: type[SrcT], dest: type[DestT]) -> _SequenceBuilder[SrcT, DestT]:
        builder = _SequenceBuilder(src, dest)
        self._sequences.append(builder.sequence)
        return builder


ProfileT = TypeVar("ProfileT", bound=Profile)


def mapping(*, cache: Cache | None = None) -> Callable[[type[ProfileT]], type[ProfileT]]:
    def decorator(cls: type[ProfileT]) -> type[ProfileT]:
        (cache or __user_cache__).add(Profile, cls)
        return cls

    return decorator
