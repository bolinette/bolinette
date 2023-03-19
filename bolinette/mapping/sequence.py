from typing import Any, Callable, Generic, TypeVar
from collections.abc import Iterator


SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)

class MappingStep(Generic[SrcT, DestT]):
    def __init__(self, func: Callable[[SrcT, DestT], None]) -> None:
        self._func = func

    def apply(self, src: SrcT, dest: DestT) -> None:
        self._func(src, dest)


class AttributeMappingStep(Generic[SrcT, DestT], MappingStep[SrcT, DestT]):
    def __init__(self, attr: str, func: Callable[[SrcT, DestT], None]) -> None:
        self._attr = attr
        MappingStep.__init__(self, func)

    @property
    def attr(self) -> str:
        return self._attr


class MappingSequence(Generic[SrcT, DestT]):
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.src = src
        self.dest = dest
        self._head: list[MappingStep[SrcT, DestT]] = []
        self._steps: list[AttributeMappingStep[SrcT, DestT]] = []
        self._tail: list[MappingStep[SrcT, DestT]] = []

    def __len__(self) -> int:
        return len(self._head) + len(self._steps) + len(self._tail)

    def __iter__(self) -> Iterator[MappingStep[Any, Any]]:
        return (s for s in [*self._head, *self._steps, *self._tail])

    def add_head_step(self, step: MappingStep[Any, Any]) -> None:
        self._head.append(step)

    def add_step(self, step: AttributeMappingStep[Any, Any]) -> None:
        self._steps.append(step)

    def add_tail_step(self, step: MappingStep[Any, Any]) -> None:
        self._tail.append(step)
