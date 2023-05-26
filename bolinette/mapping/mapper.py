from typing import Any, Callable, Protocol, TypeVar, overload

from bolinette import Cache, __core_cache__, __user_cache__, meta
from bolinette.exceptions import MappingError
from bolinette.injection import Injection, init_method, injectable
from bolinette.mapping.profiles import Profile
from bolinette.mapping.sequence import IgnoreAttribute, MapFromAttribute, MappingSequence
from bolinette.types import Type


class NoInitDestination(Protocol):
    def __init__(self) -> None:
        pass


SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)
NoInitDestT = TypeVar("NoInitDestT", bound=NoInitDestination)
TargetT = TypeVar("TargetT")


@injectable(cache=__core_cache__, strategy="singleton")
class Mapper:
    def __init__(self) -> None:
        self._sequences: dict[int, MappingSequence] = {}
        self._type_mappers: dict[Type[Any], type[TypeMapper[Any]]] = {}
        self._default_mapper: type[TypeMapper[object]] = DefaultTypeMapper

    @init_method
    def _init_profiles(self, cache: Cache, inject: Injection) -> None:
        completed: dict[int, MappingSequence] = {}
        for cls in cache.get(Profile, hint=type[Profile], raises=False):
            profile = inject.instanciate(cls)
            for sequence in profile.sequences:
                sequence.complete(completed)
                completed[hash(sequence)] = sequence
        self._sequences = completed

    @init_method
    def _init_type_mappers(self, cache: Cache) -> None:
        mappers: dict[Type[Any], type[TypeMapper[Any]]] = {}
        for cls in cache.get(TypeMapperMeta, hint=type[TypeMapper], raises=False):
            _m = meta.get(cls, TypeMapperMeta)
            mappers[_m.t] = cls
        self._type_mappers = mappers

    def add_type_mapper(self, t: Type[TargetT], mapper: "type[TypeMapper[TargetT]]") -> None:
        self._type_mappers[t] = mapper

    def set_default_type_mapper(self, mapper: "type[TypeMapper[object]]") -> None:
        self._default_mapper = mapper

    @overload
    def map(self, src_cls: type[SrcT], dest_cls: type[NoInitDestT], src: SrcT) -> NoInitDestT:
        pass

    @overload
    def map(self, src_cls: type[SrcT], dest_cls: type[DestT], src: SrcT, dest: DestT) -> DestT:
        pass

    def map(self, src_cls: type[SrcT], dest_cls: type[DestT], src: SrcT, dest: DestT | None = None) -> DestT:
        src_t = Type(src_cls)
        dest_t = Type(dest_cls)
        return MappingRunner(self._sequences, self._type_mappers, self._default_mapper).map(
            "$", src_t, dest_t, src, dest
        )


class MappingRunner:
    __slots__ = ("sequences", "mappers", "default_mapper")

    def __init__(
        self,
        sequences: dict[int, MappingSequence],
        mappers: "dict[Type[Any], type[TypeMapper[Any]]]",
        default_mapper: "type[TypeMapper[object]]",
    ) -> None:
        self.sequences = sequences
        self.mappers = mappers
        self.default_mapper = default_mapper

    def map(self, path: str, src_t: Type[SrcT], dest_t: Type[DestT], src: SrcT, dest: DestT | None) -> DestT:
        mapper_cls: type[TypeMapper[Any]] = self.mappers[dest_t] if dest_t in self.mappers else self.default_mapper
        mapper = mapper_cls(self)
        return mapper.map(path, src_t, dest_t, src, dest)


class TypeMapper(Protocol[TargetT]):
    def __init__(self, runner: MappingRunner) -> None:
        pass

    def map(
        self,
        path: str,
        src_t: Type[Any],
        dest_t: Type[TargetT],
        src: Any,
        dest: TargetT | None,
    ) -> TargetT:
        ...


TypeMapperT = TypeVar("TypeMapperT", bound=TypeMapper)


class TypeMapperMeta:
    __slots__ = "t"

    def __init__(self, t: Type[Any]) -> None:
        self.t = t


def type_mapper(
    map_for: type[Any], /, *, cache: Cache | None = None
) -> Callable[[type[TypeMapperT]], type[TypeMapperT]]:
    def decorator(cls: type[TypeMapperT]) -> type[TypeMapperT]:
        meta.set(cls, TypeMapperMeta(Type(map_for)))
        (cache or __user_cache__).add(TypeMapperMeta, cls)
        return cls

    return decorator


@type_mapper(object, cache=__core_cache__)
class DefaultTypeMapper:
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    def map(
        self,
        path: str,
        src_t: Type[SrcT],
        dest_t: Type[object],
        src: SrcT,
        dest: object | None,
    ) -> object:
        if dest is None:
            dest = dest_t.new()
        sequence: MappingSequence[SrcT, object] | None = self.runner.sequences.get(
            MappingSequence.get_hash(src_t, dest_t), None
        )
        if sequence is not None:
            for func in sequence.head:
                func.func(src, dest)
        for dest_name, anno_t in dest_t.annotations.items():
            src_name = dest_name
            sub_path = f"{path}.{dest_name}"
            if sequence is not None and dest_name in sequence.for_attrs:
                for_attr = sequence.for_attrs[dest_name]
                if isinstance(for_attr, IgnoreAttribute):
                    if not anno_t.nullable:
                        raise MappingError(f"Could not ignore attribute, type {anno_t} is not nullable", attr=sub_path)
                    setattr(dest, dest_name, None)
                    continue
                if isinstance(for_attr, MapFromAttribute):
                    src_name = for_attr.src_attr
            if not hasattr(src, src_name):
                if anno_t.nullable:
                    setattr(dest, dest_name, None)
                    continue
                else:
                    raise MappingError(
                        f"Not found in source, could not bind a None value to non nullable type {anno_t}", attr=sub_path
                    )
            value = getattr(src, src_name)
            setattr(dest, dest_name, self.runner.map(sub_path, Type(type(value)), anno_t, value, None))
        if sequence is not None:
            for func in sequence.tail:
                func.func(src, dest)
        return dest


@type_mapper(int, cache=__core_cache__)
class IntegerTypeMapper:
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    def map(
        self,
        path: str,
        src_t: Type[SrcT],
        dest_t: Type[int],
        src: SrcT,
        dest: int | None,
    ) -> int:
        try:
            return int(src)  # type: ignore
        except ValueError:
            raise MappingError(f"Could not convert value to int", attr=path)


@type_mapper(str, cache=__core_cache__)
class StringTypeMapper:
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    def map(
        self,
        path: str,
        src_t: Type[SrcT],
        dest_t: Type[str],
        src: SrcT,
        dest: str | None,
    ) -> str:
        return str(src)
