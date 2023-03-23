from typing import Any, TypeVar

from bolinette import __core_cache__, injectable, Cache, init_method, Injection
from bolinette.mapping.sequence import MappingSequence
from bolinette.mapping.profiles import Profile
from bolinette.utils import AttributeUtils


SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)


@injectable(cache=__core_cache__, strategy="singleton")
class Mapper:
    def __init__(self, attrs: AttributeUtils) -> None:
        self._attrs = attrs
        self._sequences: dict[int, MappingSequence] = {}

    @init_method
    def _init_profiles(self, cache: Cache, inject: Injection) -> None:
        for cls in cache.get(Profile, hint=type[Profile], raises=False):
            profile = inject.instanciate(cls)
            for sequence in profile.sequences:
                src, src_type_vars = self._attrs.get_generics(sequence.src)
                dest, dest_type_vars = self._attrs.get_generics(sequence.dest)
                sequence.complete(self._attrs)
                self._add_sequence(src, src_type_vars, dest, dest_type_vars, sequence)

    def map(self, src_cls: type[SrcT], dest_cls: type[DestT], src: SrcT, dest: DestT | None = None) -> DestT:
        src_cls, src_type_vars = self._attrs.get_generics(src_cls)
        dest_cls, dest_type_vars = self._attrs.get_generics(dest_cls)
        if dest is None:
            dest = dest_cls()
        sequence = self._get_sequence(src_cls, src_type_vars, dest_cls, dest_type_vars)
        for step in sequence:
            step.apply(src, dest)
        return dest

    def _get_hash(
        self,
        src: type[Any],
        src_type_vars: tuple[Any, ...],
        dest: type[Any],
        dest_type_vars: tuple[Any, ...],
    ) -> int:
        return hash((src, src_type_vars, dest, dest_type_vars))

    def _add_sequence(
        self,
        src: type[Any],
        src_type_vars: tuple[Any, ...],
        dest: type[Any],
        dest_type_vars: tuple[Any, ...],
        sequence: MappingSequence[Any, Any],
    ) -> None:
        self._sequences[self._get_hash(src, src_type_vars, dest, dest_type_vars)] = sequence

    def _has_sequence(
        self,
        src: type[Any],
        src_type_vars: tuple[Any, ...],
        dest: type[Any],
        dest_type_vars: tuple[Any, ...],
    ) -> bool:
        return self._get_hash(src, src_type_vars, dest, dest_type_vars) in self._sequences

    def _get_sequence(
        self,
        src: type[Any],
        src_type_vars: tuple[Any, ...],
        dest: type[Any],
        dest_type_vars: tuple[Any, ...],
    ) -> MappingSequence[Any, Any]:
        return self._sequences[self._get_hash(src, src_type_vars, dest, dest_type_vars)]


#     def register_mapping(self, src: type[Any], dest: type[MappingProfile]) -> None:
#         seq = _MappingSequence(self._attrs, src, dest)
#         self._profiles[hash(seq)] = seq

#     def map(self, src: dict | object, dest: DestT | type[DestT]) -> DestT:
#         return  # type: ignore


# class _MappingStep(Protocol):
#     def map(self, source: Any, dest: Any) -> None:
#         pass


# class _IgnoreStep(_MappingStep):
#     def __init__(self, attr: str, default: Any) -> None:
#         self.attr = attr
#         self.default = default

#     def map(self, source: Any, dest: Any) -> None:
#         setattr(dest, self.attr, self.default)


# class _MappingSequence:
#     def __init__(self, attrs: AttributeUtils, src: type[SrcT], dest: type[MappingProfile]) -> None:
#         self.attrs = attrs
#         self.src, self.src_typevars = self.attrs.get_generics(src, raise_on_string=True)
#         self.dest, self.dest_typevars = self.attrs.get_generics(dest, raise_on_string=True)
#         self._check_generics()
#         self.steps = self._build_steps(self.src, self.dest)

#     def _check_generics(self) -> None:
#         self._check_gen_params(self.src, self.src_typevars)
#         self._check_gen_params(self.dest, self.dest_typevars)
#         for tv in self.src_typevars:
#             if isinstance(tv, TypeVar) and tv not in self.dest_typevars:
#                 raise MappingInitError(f"TypeVar {tv} in source {self.src} was not found in destination {self.dest}")
#         for tv in self.dest_typevars:
#             if isinstance(tv, TypeVar) and tv not in self.src_typevars:
#                 raise MappingInitError(f"TypeVar {tv} in destination {self.dest} was not found in source {self.src}")

#     @staticmethod
#     def _check_gen_params(_cls: type[Any], typevars: tuple[Any, ...]) -> None:
#         if hasattr(_cls, "__parameters__"):
#             if TYPE_CHECKING:
#                 assert isinstance(_cls, _GenericOrigin)
#             if len(_cls.__parameters__) != len(typevars):
#                 raise MappingInitError(f"Mapping {_cls}, All generic params must be specified")

#     def _build_steps(self, src: type[Any], dest: type[MappingProfile]) -> list[_MappingStep]:
#         src_annotations = self.attrs.get_all_annotations(src)
#         dest_annotations = self.attrs.get_all_annotations(dest)
#         steps = []
#         for name, hint in dest_annotations.items():
#             steps.append(self._build_step(dest, name, hint, src, src_annotations))
#         return steps

#     def _build_step(
#         self,
#         dest: type[MappingProfile],
#         dest_attr: str,
#         dest_hint: type[Any],
#         src: type[Any],
#         src_annotations: dict[str, type[Any]],
#     ) -> _MappingStep:
#         default = getattr(dest, dest_attr, None)
#         if dest_attr not in src_annotations:
#             return _IgnoreStep(dest_attr, default)
#         src_hint = src_annotations[dest_attr]
#         raise MappingInitError(f"Could not map '{dest_attr}' from {dest} with source {src}")
