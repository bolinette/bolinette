from typing import Any, Protocol, TypeVar, overload

from bolinette import Cache, Injection, __core_cache__, init_method, injectable
from bolinette.mapping.profiles import Profile
from bolinette.mapping.sequence import MappingSequence
from bolinette.utils import AttributeUtils


class NoInitDestination(Protocol):
    def __init__(self) -> None:
        pass


SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)
NoInitDestT = TypeVar("NoInitDestT", bound=NoInitDestination)


@injectable(cache=__core_cache__, strategy="singleton")
class Mapper:
    def __init__(self) -> None:
        self._sequences: dict[int, MappingSequence] = {}

    @init_method
    def _init_profiles(self, cache: Cache, inject: Injection) -> None:
        completed: dict[int, MappingSequence] = {}
        for cls in cache.get(Profile, hint=type[Profile], raises=False):
            profile = inject.instanciate(cls)
            for sequence in profile.sequences:
                sequence.complete(completed)
                completed[hash(sequence)] = sequence
        self._sequences = completed

    @overload
    def map(self, src_cls: type[SrcT], dest_cls: type[NoInitDestT], src: SrcT) -> NoInitDestT:
        pass

    @overload
    def map(self, src_cls: type[SrcT], dest_cls: type[DestT], src: SrcT, dest: DestT) -> DestT:
        pass

    def map(self, src_cls: type[SrcT], dest_cls: type[DestT], src: SrcT, dest: DestT | None = None) -> DestT:
        src_cls, src_type_vars = AttributeUtils.get_generics(src_cls)
        dest_cls, dest_type_vars = AttributeUtils.get_generics(dest_cls)
        if dest is None:
            dest = dest_cls()
        sequence = self._get_sequence(MappingSequence.get_hash(src_cls, src_type_vars, dest_cls, dest_type_vars))
        for step in sequence:
            step.apply(src, dest)
        return dest

    def _add_sequence(self, sequence: MappingSequence[Any, Any]) -> None:
        self._sequences[hash(sequence)] = sequence

    def _get_sequence(self, h: int) -> MappingSequence[Any, Any]:
        return self._sequences[h]
