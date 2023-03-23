from typing import Any, Callable, Generic, TypeVar
from collections.abc import Iterator
from abc import ABC, abstractmethod

from bolinette.utils import AttributeUtils


SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)


class MappingStep(Generic[SrcT, DestT], ABC):
    @abstractmethod
    def apply(self, src: SrcT, dest: DestT) -> None:
        pass


class ToDestMappingStep(Generic[SrcT, DestT], MappingStep[SrcT, DestT], ABC):
    def __init__(self, dest: str) -> None:
        self.dest = dest


class IgnoreMappingStep(Generic[SrcT, DestT], ToDestMappingStep[SrcT, DestT]):
    def __init__(self, dest: str, default: Any) -> None:
        ToDestMappingStep.__init__(self, dest)
        self.default = default

    def apply(self, src: SrcT, dest: DestT) -> None:
        setattr(dest, self.dest, self.default)


class FromSrcMappingStep(Generic[SrcT, DestT], ToDestMappingStep[SrcT, DestT]):
    def __init__(self, src: str, dest: str, func: Callable[[SrcT, DestT], None]) -> None:
        ToDestMappingStep.__init__(self, dest)
        self.src = src
        self._func = func

    def apply(self, src: SrcT, dest: DestT) -> None:
        self._func(src, dest)


class FunctionMappingStep(Generic[SrcT, DestT], MappingStep[SrcT, DestT]):
    def __init__(self, func: Callable[[SrcT, DestT], None]) -> None:
        self._func = func

    def apply(self, src: SrcT, dest: DestT) -> None:
        self._func(src, dest)


class MappingSequence(Generic[SrcT, DestT]):
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.src = src
        self.dest = dest
        self._head: list[MappingStep[SrcT, DestT]] = []
        self._steps: dict[str, MappingStep[SrcT, DestT]] = {}
        self._tail: list[MappingStep[SrcT, DestT]] = []

    def __len__(self) -> int:
        return len(self._head) + len(self._steps) + len(self._tail)

    def __iter__(self) -> Iterator[MappingStep[Any, Any]]:
        return (s for s in [*self._head, *self._steps.values(), *self._tail])

    def __contains__(self, key: str) -> bool:
        return key in self._steps

    def add_head_step(self, step: FunctionMappingStep[Any, Any]) -> None:
        self._head.append(step)

    def add_step(self, step: ToDestMappingStep[Any, Any]) -> None:
        self._steps[step.dest] = step

    def add_tail_step(self, step: FunctionMappingStep[Any, Any]) -> None:
        self._tail.append(step)

    def complete(self, attrs: AttributeUtils) -> None:
        defined_steps = self._steps
        all_steps: dict[str, MappingStep[SrcT, DestT]] = {}
        src_attrs = attrs.get_all_annotations(self.src)
        for dest_attr, dest_hint in attrs.get_all_annotations(self.dest).items():
            if dest_attr in defined_steps:
                all_steps[dest_attr] = defined_steps[dest_attr]
                continue
            if dest_attr not in src_attrs:
                all_steps[dest_attr] = IgnoreMappingStep(dest_attr, None)
                continue

            def inner_scope(_attr: str) -> FunctionMappingStep[Any, Any]:
                return FunctionMappingStep(lambda s, d: setattr(d, _attr, getattr(s, _attr)))

            all_steps[dest_attr] = inner_scope(dest_attr)
        self._steps = all_steps
