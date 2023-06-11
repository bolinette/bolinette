from typing import Any, Callable, Protocol, TypeVar, overload

from bolinette import Cache, __core_cache__, __user_cache__, meta
from bolinette.exceptions import MappingError
from bolinette.injection import Injection, init_method, injectable
from bolinette.mapping.profiles import Profile, MapFromOptions
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


class DefaultTypeMapper:
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    def map(
        self,
        path: str,
        src_t: Type[SrcT],
        dest_t: Type[Any],
        src: SrcT,
        dest: Any | None,
    ) -> Any:
        if dest_t.cls in (list, tuple, set):
            return self._map_iterable(path, src_t, dest_t, src, dest)
        if dest_t.cls is dict:
            return self._map_dict(path, dest_t, src, dest)
        return self._map_object(path, src_t, dest_t, src, dest)

    def _map_object(
        self,
        path: str,
        src_t: Type[SrcT],
        dest_t: Type[Any],
        src: SrcT,
        dest: Any | None,
    ) -> Any:
        if dest_t.is_any:
            return self.runner.map(path, src_t, src_t, src, None)
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
            selected_t: Type[Any] | None = None
            if sequence is not None and dest_name in sequence.for_attrs:
                for_attr = sequence.for_attrs[dest_name]
                if isinstance(for_attr, IgnoreAttribute):
                    if not anno_t.nullable:
                        raise MappingError(f"Could not ignore attribute, type {anno_t} is not nullable", attr=sub_path)
                    setattr(dest, dest_name, None)
                    continue
                if isinstance(for_attr, MapFromAttribute):
                    src_name = for_attr.src_attr
                    selected_t = for_attr.use_type
            if not hasattr(src, src_name):
                if anno_t.nullable:
                    setattr(dest, dest_name, None)
                    continue
                else:
                    raise MappingError(
                        f"Not found in source, could not bind a None value to non nullable type {anno_t}", attr=sub_path
                    )
            if anno_t.is_union:
                if selected_t is None:
                    raise MappingError(
                        f"Destination type {anno_t} is a union, "
                        f"please use '{MapFromOptions.use_type.__name__}' in profile",
                        attr=sub_path,
                    )
                if selected_t != anno_t and selected_t not in anno_t.union:
                    raise MappingError(f"Selected type {selected_t} is not assignable to {anno_t}", attr=sub_path)
                anno_t = selected_t
            value = getattr(src, src_name)
            setattr(dest, dest_name, self.runner.map(sub_path, Type(type(value)), anno_t, value, None))
        if sequence is not None:
            for func in sequence.tail:
                func.func(src, dest)
        return dest

    def _map_iterable(
        self,
        path: str,
        src_t: Type[SrcT],
        dest_t: Type[list[DestT]] | Type[set[DestT]] | Type[tuple[DestT]],
        src: SrcT,
        dest: list[DestT] | set[DestT] | tuple[DestT] | None,
    ) -> list[DestT] | set[DestT] | tuple[DestT]:
        elems = []
        if not hasattr(src, "__iter__"):
            raise MappingError(f"Could not map non iterable type {src_t} to {dest_t}", attr=path)
        for index, elem in enumerate(src):  # type: ignore
            elems.append(
                self.runner.map(f"{path}.[{index}]", Type.from_instance(elem), Type(dest_t.vars[0]), elem, None)
            )
        if dest is None:
            dest = dest_t.new(elems)
        elif isinstance(dest, list):
            dest.clear()
            dest.extend(elems)
        elif isinstance(dest, set):
            dest.clear()
            dest.update(elems)
        elif isinstance(dest, tuple):
            raise MappingError("Could not use an existing tuple instance, tuples are immutable", attr=path)
        return dest

    def _map_dict(
        self,
        path: str,
        dest_t: Type[dict[str, DestT]],
        src: object,
        dest: dict[str, DestT] | None,
    ) -> dict[str, DestT]:
        if dest is None:
            dest = dest_t.new()
        for src_name, src_value in vars(src).items():
            sub_path = f"{path}['{src_name}']"
            dest[src_name] = self.runner.map(
                sub_path, Type.from_instance(src_value), Type(dest_t.vars[1]), src_value, None
            )
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
            raise MappingError(f"Could not convert value '{src}' to int", attr=path)


@type_mapper(float, cache=__core_cache__)
class FloatTypeMapper:
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    def map(
        self,
        path: str,
        src_t: Type[SrcT],
        dest_t: Type[float],
        src: SrcT,
        dest: float | None,
    ) -> float:
        try:
            return float(src)  # type: ignore
        except ValueError:
            raise MappingError(f"Could not convert value '{src}' to float", attr=path)


@type_mapper(bool, cache=__core_cache__)
class BoolTypeMapper:
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    def map(
        self,
        path: str,
        src_t: Type[SrcT],
        dest_t: Type[bool],
        src: SrcT,
        dest: bool | None,
    ) -> bool:
        return bool(src)


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
