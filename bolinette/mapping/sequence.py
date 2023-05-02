from collections.abc import Iterator
from typing import Any, Callable, Generic, Protocol, TypeVar

from bolinette.exceptions import InitMappingError, MappingError
from bolinette.types import Type

SrcT = TypeVar("SrcT", bound=object)
SrcT_contra = TypeVar("SrcT_contra", bound=object, contravariant=True)
DestT = TypeVar("DestT", bound=object)
DestT_contra = TypeVar("DestT_contra", bound=object, contravariant=True)


class MappingStep(Protocol[SrcT_contra, DestT_contra]):
    def apply(self, src: SrcT_contra, dest: DestT_contra) -> None:
        pass


class ToDestMappingStep(MappingStep[SrcT_contra, DestT_contra], Protocol[SrcT_contra, DestT_contra]):
    dest_cls: type[Any]
    dest_attr: str


class IgnoreMappingStep(Generic[SrcT, DestT], ToDestMappingStep[SrcT, DestT]):
    def __init__(self, dest_cls: type[Any], dest_attr: str, hints: tuple[type[Any] | None, ...]) -> None:
        self.dest_cls = dest_cls
        self.dest_attr = dest_attr
        if None in hints:
            self.default = None
        else:
            try:
                for hint in hints:
                    self.default = hint()  # type: ignore
                    break
            except TypeError as err:
                raise MappingError(
                    "Default value for attribute could not be determined",
                    cls=self.dest_cls,
                    attr=self.dest_attr,
                ) from err

    def apply(self, src: SrcT, dest: DestT) -> None:
        setattr(dest, self.dest_attr, self.default)


class TryMappingStep(Generic[SrcT, DestT], IgnoreMappingStep[SrcT, DestT]):
    def __init__(
        self,
        dest_cls: type,
        dest_attr: str,
        hints: tuple[type | None],
    ) -> None:
        super().__init__(dest_cls, dest_attr, hints)

    def apply(self, src: SrcT, dest: DestT) -> None:
        if hasattr(src, self.dest_attr):
            setattr(dest, self.dest_attr, getattr(src, self.dest_attr))
        else:
            super().apply(src, dest)


class FromSrcMappingStep(Generic[SrcT, DestT], ToDestMappingStep[SrcT, DestT]):
    def __init__(
        self,
        src_cls: type[Any],
        src_attr: str,
        dest_cls: type[Any],
        dest_attr: str,
        func: Callable[[SrcT, DestT], None],
    ) -> None:
        self.src_cls = src_cls
        self.src_attr = src_attr
        self.dest_cls = dest_cls
        self.dest_attr = dest_attr
        self.func = func

    def apply(self, src: SrcT, dest: DestT) -> None:
        self.func(src, dest)


class FunctionMappingStep(Generic[SrcT, DestT], MappingStep[SrcT, DestT]):
    def __init__(self, func: Callable[[SrcT, DestT], None]) -> None:
        self.func = func

    def apply(self, src: SrcT, dest: DestT) -> None:
        self.func(src, dest)


class IncludeFromBase:
    def __init__(self, src_cls: type[Any], dest_cls: type[Any]) -> None:
        self.src_cls = src_cls
        self.dest_cls = dest_cls


class MappingSequence(Generic[SrcT, DestT]):
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.src_t = Type(src)
        self.dest_t = Type(dest)
        self.src_hints = self.src_t.get_annotations()
        self.dest_hints = self.dest_t.get_annotations()
        self.head: list[MappingStep[SrcT, DestT]] = []
        self.steps: dict[str, MappingStep[SrcT, DestT]] = {}
        self.tail: list[MappingStep[SrcT, DestT]] = []
        self.includes: list[IncludeFromBase] = []

    @staticmethod
    def get_hash(
        src_t: Type[Any],
        dest_t: Type[Any],
    ) -> int:
        return hash((src_t, dest_t))

    def __hash__(self) -> int:
        return MappingSequence.get_hash(self.src_t, self.dest_t)

    def __iter__(self) -> Iterator[MappingStep[Any, Any]]:
        return (s for s in [*self.head, *self.steps.values(), *self.tail])

    def add_head_step(self, step: FunctionMappingStep[Any, Any]) -> None:
        self.head.append(step)

    def add_step(self, step: ToDestMappingStep) -> None:
        self.steps[step.dest_attr] = step

    def add_tail_step(self, step: FunctionMappingStep[Any, Any]) -> None:
        self.tail.append(step)

    def add_include(self, include: IncludeFromBase) -> None:
        self.includes.append(include)

    def complete(self, completed_sequences: "dict[int, MappingSequence]") -> None:
        defined_steps = self.steps

        incl_head: list[MappingStep] = []
        incl_tail: list[MappingStep] = []
        incl_steps: dict[str, MappingStep[SrcT, DestT]] = {}
        for included in self.includes:
            incl_src_t = Type(included.src_cls)
            incl_dest_t = Type(included.dest_cls)
            incl_hash = MappingSequence.get_hash(incl_src_t, incl_dest_t)
            if incl_hash not in completed_sequences:
                raise InitMappingError(
                    f"Mapping ({self.src_t} -> {self.dest_t}): "
                    f"Could not find base mapping ({incl_src_t} -> {incl_dest_t}). "
                    f"Make sure the mappings are declared in the right order."
                )
            incl_sequence = completed_sequences[incl_hash]
            incl_head = [*incl_head, *incl_sequence.head]
            incl_tail = [*incl_tail, *incl_sequence.tail]
            incl_steps |= incl_sequence.steps
        self.head = [*incl_head, *self.head]
        self.tail = [*incl_tail, *self.tail]

        all_steps: dict[str, MappingStep[SrcT, DestT]] = {}
        for dest_attr, dest_hint in self.dest_hints.items():
            if dest_attr in defined_steps:
                all_steps[dest_attr] = defined_steps[dest_attr]
                continue
            if dest_attr in incl_steps:
                all_steps[dest_attr] = incl_steps[dest_attr]
                continue
            if dest_attr not in self.src_hints:
                all_steps[dest_attr] = TryMappingStep(self.dest_t.cls, dest_attr, dest_hint)
                continue

            def inner_scope(_attr: str) -> FunctionMappingStep[Any, Any]:
                return FunctionMappingStep(lambda s, d: setattr(d, _attr, getattr(s, _attr)))

            all_steps[dest_attr] = inner_scope(dest_attr)
        self.steps = all_steps

    def check_type(self, src_hint: tuple[type | None, ...], dest_hint: tuple[type | None, ...]) -> None:
        for cls in dest_hint:
            if cls is None:
                continue
