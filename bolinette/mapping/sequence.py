from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, Callable, Generic, TypeVar

from bolinette.exceptions import InitError, MappingError
from bolinette.utils import AttributeUtils

SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)


class MappingStep(Generic[SrcT, DestT], ABC):
    @abstractmethod
    def apply(self, src: SrcT, dest: DestT) -> None:
        pass


class ToDestMappingStep(Generic[SrcT, DestT], MappingStep[SrcT, DestT], ABC):
    def __init__(self, dest_cls: type[Any], dest_attr: str) -> None:
        self.dest_cls = dest_cls
        self.dest_attr = dest_attr


class IgnoreMappingStep(Generic[SrcT, DestT], ToDestMappingStep[SrcT, DestT]):
    def __init__(self, dest_cls: type[Any], dest_attr: str, hints: tuple[type[Any] | None]) -> None:
        ToDestMappingStep.__init__(self, dest_cls, dest_attr)
        if None in hints:
            self.default = None
        else:
            for hint in hints:
                if hint is None:
                    continue
                self.default = hint()
                break
            else:
                raise MappingError(
                    "Default value for attribute could not be determined",
                    cls=self.dest_cls,
                    attr=self.dest_attr,
                )

    def apply(self, src: SrcT, dest: DestT) -> None:
        setattr(dest, self.dest_attr, self.default)


class FromSrcMappingStep(Generic[SrcT, DestT], ToDestMappingStep[SrcT, DestT]):
    def __init__(
        self,
        src_cls: type[Any],
        src_attr: str,
        dest_cls: type[Any],
        dest_attr: str,
        func: Callable[[SrcT, DestT], None],
    ) -> None:
        ToDestMappingStep.__init__(self, dest_cls, dest_attr)
        self.src_cls = src_cls
        self.src_attr = src_attr
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
        self.src_cls, self.src_type_vars = AttributeUtils.get_generics(src)
        self.dest_cls, self.dest_type_vars = AttributeUtils.get_generics(dest)
        self.src_hints = AttributeUtils.get_all_annotations(self.src_cls)
        self.dest_hints = AttributeUtils.get_all_annotations(self.dest_cls)
        self._head: list[MappingStep[SrcT, DestT]] = []
        self._steps: dict[str, MappingStep[SrcT, DestT]] = {}
        self._tail: list[MappingStep[SrcT, DestT]] = []

    def __hash__(self) -> int:
        return hash((self.src_cls, self.src_type_vars, self.dest_cls, self.dest_type_vars))

    def __len__(self) -> int:
        return len(self._head) + len(self._steps) + len(self._tail)

    def __iter__(self) -> Iterator[MappingStep[Any, Any]]:
        return (s for s in [*self._head, *self._steps.values(), *self._tail])

    def __contains__(self, key: str) -> bool:
        return key in self._steps

    def add_head_step(self, step: FunctionMappingStep[Any, Any]) -> None:
        self._head.append(step)

    def add_step(self, step: ToDestMappingStep[Any, Any]) -> None:
        self._steps[step.dest_attr] = step

    def add_tail_step(self, step: FunctionMappingStep[Any, Any]) -> None:
        self._tail.append(step)

    def complete(self) -> None:
        defined_steps = self._steps
        all_steps: dict[str, MappingStep[SrcT, DestT]] = {}
        for dest_attr, dest_hint in self.dest_hints.items():
            if dest_attr in defined_steps:
                all_steps[dest_attr] = defined_steps[dest_attr]
                continue
            if dest_attr not in self.src_hints:
                all_steps[dest_attr] = IgnoreMappingStep(self.dest_cls, dest_attr, dest_hint)
                continue

            def inner_scope(_attr: str) -> FunctionMappingStep[Any, Any]:
                return FunctionMappingStep(lambda s, d: setattr(d, _attr, getattr(s, _attr)))

            all_steps[dest_attr] = inner_scope(dest_attr)
        self._steps = all_steps
