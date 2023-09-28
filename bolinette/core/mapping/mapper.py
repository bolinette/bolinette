from collections.abc import Callable, Iterable
from typing import Any, Protocol, TypeGuard, TypeVar, overload

from typing_extensions import override

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.injection import Injection, init_method
from bolinette.core.mapping.exceptions import (
    ConvertionError,
    DestinationNotNullableError,
    IgnoreImpossibleError,
    ImmutableCollectionError,
    InstanciationError,
    SourceNotFoundError,
    TypeMismatchError,
    TypeNotIterableError,
    UnionNotAllowedError,
)
from bolinette.core.mapping.profiles import Profile
from bolinette.core.mapping.sequence import IgnoreAttribute, MapFromAttribute, MappingSequence
from bolinette.core.types import Type


class NoInitDestination(Protocol):
    def __init__(self) -> None:
        pass


SrcT = TypeVar("SrcT", bound=object)
DestT = TypeVar("DestT", bound=object)
NoInitDestT = TypeVar("NoInitDestT", bound=NoInitDestination)
TargetT = TypeVar("TargetT")


class Mapper:
    def __init__(self) -> None:
        self._sequences: dict[int, MappingSequence[Any, Any]] = {}
        self._type_mappers: dict[Type[Any], type[TypeMapper[Any]]] = {}
        self._default_mapper: type[TypeMapper[object]] = DefaultTypeMapper

    @init_method
    def _init_profiles(self, cache: Cache, inject: Injection) -> None:
        completed: dict[int, MappingSequence[Any, Any]] = {}
        for cls in cache.get(Profile, hint=type[Profile], raises=False):
            profile = inject.instantiate(cls)
            for sequence in profile.sequences:
                sequence.complete(completed)
                completed[hash(sequence)] = sequence
        self._sequences = completed

    @init_method
    def _init_type_mappers(self, cache: Cache) -> None:
        mappers: dict[Type[Any], type[TypeMapper[Any]]] = {}
        for cls in cache.get(TypeMapperMeta, hint=type[TypeMapper[Any]], raises=False):
            _m = meta.get(cls, TypeMapperMeta)
            mappers[_m.t] = cls
        self._type_mappers = mappers

    def add_type_mapper(self, t: Type[TargetT], mapper: "type[TypeMapper[TargetT]]") -> None:
        self._type_mappers[t] = mapper

    def set_default_type_mapper(self, mapper: "type[TypeMapper[object]]") -> None:
        self._default_mapper = mapper

    @overload
    def map(
        self,
        src_cls: type[SrcT],
        dest_cls: type[NoInitDestT],
        src: SrcT,
        *,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
    ) -> NoInitDestT:
        pass

    @overload
    def map(
        self,
        src_cls: type[SrcT],
        dest_cls: type[DestT],
        src: SrcT,
        dest: DestT,
        *,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
    ) -> DestT:
        pass

    def map(
        self,
        src_cls: type[SrcT],
        dest_cls: type[DestT],
        src: SrcT,
        dest: DestT | None = None,
        *,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
    ) -> DestT:
        src_t = Type(src_cls)
        dest_t = Type(dest_cls)
        return MappingRunner(self._sequences, self._type_mappers, self._default_mapper).map(
            src_expr or ExpressionTree.new(src_t),
            src_t,
            dest_expr or ExpressionTree.new(dest_t),
            dest_t,
            src,
            dest,
        )


class MappingRunner:
    __slots__ = ("sequences", "mappers", "default_mapper")

    def __init__(
        self,
        sequences: dict[int, MappingSequence[Any, Any]],
        mappers: "dict[Type[Any], type[TypeMapper[Any]]]",
        default_mapper: "type[TypeMapper[object]]",
    ) -> None:
        self.sequences = sequences
        self.mappers = mappers
        self.default_mapper = default_mapper

    def map(
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[DestT],
        src: SrcT,
        dest: DestT | None,
    ) -> DestT:
        if src is None:
            if not dest_t.nullable:
                raise DestinationNotNullableError(src_expr, dest_expr, dest_t)
            return None  # type: ignore
        mapper_cls: type[TypeMapper[Any]] = self.mappers[dest_t] if dest_t in self.mappers else self.default_mapper
        mapper = mapper_cls(self)
        return mapper.map(src_expr, src_t, dest_expr, dest_t, src, dest)


class TypeMapper(Protocol[TargetT]):
    def __init__(self, runner: MappingRunner) -> None:
        pass

    def map(
        self,
        src_expr: ExpressionNode,
        src_t: Type[Any],
        dest_expr: ExpressionNode,
        dest_t: Type[TargetT],
        src: Any,
        dest: TargetT | None,
    ) -> TargetT:
        ...


TypeMapperT = TypeVar("TypeMapperT", bound=TypeMapper[Any])


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


class DefaultTypeMapper(TypeMapper[object]):
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    @override
    def map(
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[Any],
        src: SrcT,
        dest: Any | None,
    ) -> Any:
        if dest_t.cls in (list, tuple, set):
            return self._map_iterable(src_expr, src_t, dest_expr, dest_t, src, dest)
        if dest_t.cls is dict:
            return self._map_dict(src_expr, dest_expr, dest_t, src, dest)
        return self._map_object(src_expr, src_t, dest_expr, dest_t, src, dest)

    def _map_object(
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[Any],
        src: SrcT,
        dest: Any | None,
    ) -> Any:
        if dest_t.is_any:
            return self.runner.map(src_expr, src_t, dest_expr, src_t, src, None)
        if dest is None:
            try:
                dest = dest_t.new()
            except TypeError:
                raise InstanciationError(dest_expr, dest_t)
        sequence: MappingSequence[SrcT, object] | None = self.runner.sequences.get(
            MappingSequence.get_hash(src_t, dest_t), None
        )
        if sequence is not None:
            for func in sequence.head:
                func.func(src, dest)
        for dest_name, anno_t in dest_t.annotations().items():
            src_name = dest_name
            field_src_expr = self._get_expr(src_expr, src, src_name)
            field_dest_expr: ExpressionNode = getattr(dest_expr, dest_name)
            selected_t: Type[Any] | None = None
            src_value_expr = self._get_expr(ExpressionTree.new(src_t), src, src_name)
            if sequence is not None and dest_name in sequence.for_attrs:
                for_attr = sequence.for_attrs[dest_name]
                if isinstance(for_attr, IgnoreAttribute):
                    if not anno_t.nullable:
                        raise IgnoreImpossibleError(field_dest_expr, anno_t)
                    setattr(dest, dest_name, None)
                    continue
                if isinstance(for_attr, MapFromAttribute):
                    src_value_expr = for_attr.src_expr
                    selected_t = for_attr.use_type
            if anno_t.is_union:
                if selected_t is None:
                    raise UnionNotAllowedError(field_dest_expr, anno_t)
                if selected_t != anno_t and selected_t not in anno_t.union:
                    raise TypeMismatchError(field_src_expr, field_dest_expr, selected_t, anno_t)
                anno_t = selected_t
            try:
                value = ExpressionTree.get_value(src_value_expr, src)
            except Exception:
                if not self._has_default_value(dest, dest_name):
                    if not anno_t.nullable:
                        raise SourceNotFoundError(field_src_expr, field_dest_expr, anno_t)
                    else:
                        setattr(dest, dest_name, None)
                        continue
                else:
                    setattr(dest, dest_name, self._get_default_value(dest, dest_name))
                    continue
            setattr(
                dest,
                dest_name,
                self.runner.map(field_src_expr, Type(type(value)), field_dest_expr, anno_t, value, None),
            )
        if sequence is not None:
            for func in sequence.tail:
                func.func(src, dest)
        return dest

    def _map_iterable(
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[list[DestT]] | Type[set[DestT]] | Type[tuple[DestT]],
        src: SrcT,
        dest: list[DestT] | set[DestT] | tuple[DestT] | None,
    ) -> list[DestT] | set[DestT] | tuple[DestT]:
        elems: list[DestT] = []
        if not self._is_iterable(src):
            raise TypeNotIterableError(src_expr, dest_expr, src_t, dest_t)
        for index, elem in enumerate(src):
            elems.append(
                self.runner.map(
                    src_expr[index],
                    Type.from_instance(elem),
                    dest_expr[index],
                    Type(dest_t.vars[0]),
                    elem,
                    None,
                )
            )
        if dest is None:
            dest = dest_t.new(elems)
        elif isinstance(dest, list):
            dest.clear()
            dest.extend(elems)
        elif isinstance(dest, set):
            dest.clear()
            dest.update(elems)
        else:
            raise ImmutableCollectionError(dest_expr)
        return dest

    def _map_dict(
        self,
        src_expr: ExpressionNode,
        dest_expr: ExpressionNode,
        dest_t: Type[dict[str, DestT]],
        src: object,
        dest: dict[str, DestT] | None,
    ) -> dict[str, DestT]:
        if dest is None:
            dest = dest_t.new()
        for src_name, src_value in self._iter_obj(src):
            dest[src_name] = self.runner.map(
                src_expr[src_name],
                Type.from_instance(src_value),
                getattr(dest_expr, src_name),
                Type(dest_t.vars[1]),
                src_value,
                None,
            )
        return dest

    @staticmethod
    def _has_attr(obj: object, attr: str) -> bool:
        if isinstance(obj, dict):
            return attr in obj
        return hasattr(obj, attr)

    @staticmethod
    def _has_default_value(obj: object, attr: str) -> bool:
        return hasattr(type(obj), attr)

    @staticmethod
    def _get_default_value(obj: object, attr: str) -> Any:
        return getattr(type(obj), attr)

    @staticmethod
    def _get_value(obj: object, attr: str) -> Any:
        if isinstance(obj, dict):
            return obj[attr]  # pyright: ignore[reportUnknownVariableType]
        return getattr(obj, attr)

    @staticmethod
    def _get_expr(path: ExpressionNode, obj: Any, attr: str) -> ExpressionNode:
        if isinstance(obj, dict):
            return path[attr]
        return getattr(path, attr)

    @staticmethod
    def _iter_obj(obj: object) -> Iterable[tuple[str, Any]]:
        if isinstance(obj, dict):
            return obj.items()  # pyright: ignore[reportUnknownVariableType]
        return vars(obj).items()

    @staticmethod
    def _is_iterable(obj: Any) -> TypeGuard[Iterable[Any]]:
        return hasattr(obj, "__iter__")


class IntegerTypeMapper(TypeMapper[int]):
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    @override
    def map(
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[int],
        src: SrcT,
        dest: int | None,
    ) -> int:
        try:
            return int(src)  # type: ignore
        except (ValueError, TypeError) as err:
            raise ConvertionError(src_expr, dest_expr, src, Type(int)) from err


class FloatTypeMapper(TypeMapper[float]):
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    @override
    def map(
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[float],
        src: SrcT,
        dest: float | None,
    ) -> float:
        try:
            return float(src)  # type: ignore
        except ValueError as err:
            raise ConvertionError(src_expr, dest_expr, src, Type(float)) from err


class BoolTypeMapper(TypeMapper[bool]):
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    @override
    def map(
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[bool],
        src: SrcT,
        dest: bool | None,
    ) -> bool:
        return bool(src)


class StringTypeMapper(TypeMapper[str]):
    __slots__ = "runner"

    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    @override
    def map(
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[str],
        src: SrcT,
        dest: str | None,
    ) -> str:
        return str(src)
