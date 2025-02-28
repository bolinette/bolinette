from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Any, Literal, Protocol, TypeGuard, overload, override
from typing import TypedDict as TypedDict

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.injection import Injection, post_init
from bolinette.core.mapping.exceptions import (
    ConvertionError,
    DestinationNotNullableError,
    IgnoreImpossibleError,
    ImmutableCollectionError,
    InstantiationError,
    LiteralMatchingError,
    MappingError,
    SourceNotFoundError,
    TypeMismatchError,
    TypeNotIterableError,
    UnionError,
    ValidationError,
)
from bolinette.core.mapping.profiles import Profile
from bolinette.core.mapping.sequence import IgnoreAttribute, MapFromAttribute, MappingSequence
from bolinette.core.types import Type, TypeCollection


class NoInitDestination(Protocol):
    def __init__(self) -> None:
        pass


class Mapper:
    def __init__(self) -> None:
        self._sequences: dict[int, MappingSequence[Any, Any]] = {}
        self._type_mappers: TypeCollection[type[MappingWorker[Any]]] = TypeCollection()
        self._default_mapper: type[MappingWorker[object]] = ObjectMapper

    @post_init
    def _init_profiles(self, cache: Cache, inject: Injection) -> None:
        completed: dict[int, MappingSequence[Any, Any]] = {}
        for cls in cache.get(Profile, hint=type[Profile], raises=False):
            profile = inject.instantiate(cls)
            for sequence in profile.sequences:
                sequence.complete(completed)
                completed[hash(sequence)] = sequence
        self._sequences = completed

    @post_init
    def _init_type_mappers(self, cache: Cache) -> None:
        for cls in cache.get(MappingWorkerMeta, hint=type[MappingWorker[Any]], raises=False):
            _m = meta.get(cls, MappingWorkerMeta)
            self.add_type_mapper(_m.t, _m.match_all)

    def add_type_mapper[T: MappingWorker[Any]](self, mapper_t: Type[T], match_all: bool) -> None:
        mapper_base = next(b for b in mapper_t.bases if b.cls is MappingWorker)
        mapped_t = Type(mapper_base.vars[0])
        if mapped_t.is_union:
            for t in mapped_t.union:
                self._type_mappers.add(t, mapper_t.cls, match_all=match_all)
        else:
            self._type_mappers.add(mapped_t, mapper_t.cls, match_all=match_all)

    def set_default_type_mapper(self, mapper: "type[MappingWorker[object]]") -> None:
        self._default_mapper = mapper

    @overload
    def map[SrcT, DestT: NoInitDestination](
        self,
        src_cls: type[SrcT],
        dest_cls: type[DestT],
        src: SrcT,
        *,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
        validate: bool = False,
    ) -> DestT:
        pass

    @overload
    def map[SrcT, DestT](
        self,
        src_cls: type[SrcT],
        dest_cls: type[DestT],
        src: SrcT,
        dest: DestT,
        *,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
        validate: bool = False,
    ) -> DestT:
        pass

    def map[SrcT, DestT](
        self,
        src_cls: type[SrcT],
        dest_cls: type[DestT],
        src: SrcT,
        dest: DestT | None = None,
        *,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
        validate: bool = False,
    ) -> DestT:
        src_t = Type(src_cls)
        dest_t = Type(dest_cls)

        exc_grp: list[MappingError] | None
        if validate:
            exc_grp = []
        else:
            exc_grp = None

        mapped = MappingRunner(self._sequences, self._type_mappers, self._default_mapper).map(
            src_expr or ExpressionTree.new(src_t),
            src_t,
            dest_expr or ExpressionTree.new(dest_t),
            dest_t,
            src,
            dest,
            exc_grp,
        )
        if exc_grp is not None and len(exc_grp) > 0:
            raise ValidationError(exc_grp)
        return mapped


class MappingRunner:
    def __init__(
        self,
        sequences: dict[int, MappingSequence[Any, Any]],
        mappers: "TypeCollection[type[MappingWorker[Any]]]",
        default_mapper: "type[MappingWorker[object]]",
    ) -> None:
        self.sequences = sequences
        self.mappers = mappers
        self.default_mapper = default_mapper
        self._mapper_cache: dict[type[MappingWorker[Any]], MappingWorker[Any]] = {}

    def map[SrcT, DestT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[DestT],
        src: SrcT,
        dest: DestT | None,
        exc_grp: list[MappingError] | None,
    ) -> DestT:
        if src is None:
            if not dest_t.nullable:
                exc = DestinationNotNullableError(src_expr, dest_expr, dest_t)
                if exc_grp is None:
                    raise exc
                exc_grp.append(exc)
                return None  # pyright: ignore
            return None  # pyright: ignore

        mapper_cls: type[MappingWorker[Any]]
        if self.mappers.has(dest_t):
            mapper_cls = self.mappers.get(dest_t)
        else:
            mapper_cls = self.default_mapper

        if mapper_cls in self._mapper_cache:
            mapper = self._mapper_cache[mapper_cls]
        else:
            mapper = mapper_cls(self)
            self._mapper_cache[mapper_cls] = mapper

        return mapper.map(src_expr, src_t, dest_expr, dest_t, src, dest, exc_grp)


class MappingWorker[TargetT](ABC):
    def __init__(self, runner: MappingRunner) -> None:
        self.runner = runner

    @abstractmethod
    def map(
        self,
        src_expr: ExpressionNode,
        src_t: Type[Any],
        dest_expr: ExpressionNode,
        dest_t: Type[TargetT],
        src: Any,
        dest: TargetT | None,
        exc_grp: list[MappingError] | None,
    ) -> TargetT: ...


class MappingWorkerMeta:
    def __init__(self, t: Type[Any], match_all: bool) -> None:
        self.t = t
        self.match_all = match_all


def mapping_worker[TypeMapperT: MappingWorker[Any]](
    *, cache: Cache | None = None, match_all: bool = False
) -> Callable[[type[TypeMapperT]], type[TypeMapperT]]:
    def decorator(cls: type[TypeMapperT]) -> type[TypeMapperT]:
        meta.set(cls, MappingWorkerMeta(Type(cls), match_all))
        (cache or __user_cache__).add(MappingWorkerMeta, cls)
        return cls

    return decorator


class ObjectMapper(MappingWorker[Any]):
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[Any],
        src: SrcT,
        dest: Any | None,
        exc_grp: list[MappingError] | None,
    ) -> Any:
        if dest_t.is_union:
            union_errors: dict[Type[Any], list[MappingError]] = {}
            for possible_t in dest_t.union:
                sub_exc_grp: list[MappingError] | None = None
                try:
                    if exc_grp is None:
                        sub_exc_grp = None
                    else:
                        sub_exc_grp = []
                    return self.runner.map(src_expr, src_t, dest_expr, possible_t, src, dest, sub_exc_grp)
                except MappingError as err:
                    union_errors[possible_t] = [err]
                    continue
                finally:
                    if sub_exc_grp is not None:
                        union_errors[possible_t] = sub_exc_grp
            exc = UnionError(src_expr, dest_t, union_errors)
            if exc_grp is None:
                raise exc
            exc_grp.append(exc)
            return None

        if dest_t.is_any:
            return self.runner.map(src_expr, src_t, dest_expr, src_t, src, None, exc_grp)
        if dest is None:
            try:
                dest = dest_t.new()
            except TypeError as e:
                exc = InstantiationError(dest_expr, dest_t)
                if exc_grp is None:
                    raise exc from e
                exc_grp.append(exc)
                return None
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
                        exc = IgnoreImpossibleError(field_dest_expr, anno_t)
                        if exc_grp is None:
                            raise exc
                        exc_grp.append(exc)
                        continue
                    setattr(dest, dest_name, None)
                    continue
                if isinstance(for_attr, MapFromAttribute):
                    src_value_expr = for_attr.src_expr
                    selected_t = for_attr.use_type
            if anno_t.is_union and selected_t is not None:
                if selected_t not in anno_t.union:
                    exc = TypeMismatchError(field_src_expr, field_dest_expr, selected_t, anno_t)
                    if exc_grp is None:
                        raise exc
                    exc_grp.append(exc)
                    continue
                anno_t = selected_t
            try:
                value = ExpressionTree.get_value(src_value_expr, src)
            except (AttributeError, KeyError) as err:
                if not anno_t.required or not dest_t.total:
                    continue
                if not self._has_default_value(dest, dest_name):
                    if not anno_t.nullable:
                        exc = SourceNotFoundError(field_src_expr, field_dest_expr, anno_t)
                        if exc_grp is None:
                            raise exc from err
                        exc_grp.append(exc)
                        continue
                    else:
                        setattr(dest, dest_name, None)
                        continue
                else:
                    setattr(dest, dest_name, self._get_default_value(dest, dest_name))
                    continue
            new_value = self.runner.map(
                field_src_expr,
                Type(type(value)),  # pyright: ignore[reportUnknownArgumentType]
                field_dest_expr,
                anno_t,
                value,
                None,
                exc_grp,
            )
            self._set_attr(dest, dest_name, new_value)
        if sequence is not None:
            for func in sequence.tail:
                func.func(src, dest)
        return dest

    @staticmethod
    def _has_default_value(obj: object, attr: str) -> bool:
        return hasattr(type(obj), attr)

    @staticmethod
    def _get_default_value(obj: object, attr: str) -> Any:
        return getattr(type(obj), attr)

    @staticmethod
    def _get_expr(path: ExpressionNode, obj: Any, attr: str) -> ExpressionNode:
        if isinstance(obj, dict):
            return path[attr]
        return getattr(path, attr)

    @staticmethod
    def _set_attr(obj: Any | dict[str, Any], key: str, value: Any) -> None:
        if isinstance(obj, dict):
            obj[key] = value
        else:
            setattr(obj, key, value)


class IntegerMapper(MappingWorker[int]):
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[int],
        src: SrcT,
        dest: int | None,
        exc_grp: list[MappingError] | None,
    ) -> int:
        try:
            return int(src)  # pyright: ignore[reportArgumentType]
        except (ValueError, TypeError) as err:
            exc = ConvertionError(src_expr, dest_expr, src, Type(int))
            if exc_grp is None:
                raise exc from err
            exc_grp.append(exc)
            return None  # pyright: ignore[reportReturnType]


class FloatMapper(MappingWorker[float]):
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[float],
        src: SrcT,
        dest: float | None,
        exc_grp: list[MappingError] | None,
    ) -> float:
        try:
            return float(src)  # pyright: ignore[reportArgumentType]
        except ValueError as err:
            exc = ConvertionError(src_expr, dest_expr, src, Type(float))
            if exc_grp is None:
                raise exc from err
            exc_grp.append(exc)
            return None  # pyright: ignore[reportReturnType]


class BoolMapper(MappingWorker[bool]):
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[bool],
        src: SrcT,
        dest: bool | None,
        exc_grp: list[MappingError] | None,
    ) -> bool:
        return bool(src)


class StringMapper(MappingWorker[str]):
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[str],
        src: SrcT,
        dest: str | None,
        exc_grp: list[MappingError] | None,
    ) -> str:
        return str(src)


class BytesMapper(MappingWorker[bytes]):
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[bytes],
        src: SrcT,
        dest: bytes | None,
        exc_grp: list[MappingError] | None,
    ) -> bytes:
        if isinstance(src, str):
            return src.encode("utf-8")
        if isinstance(src, bytes):
            return bytes(src)
        exc = ConvertionError(src_expr, dest_expr, src, Type(bytes))
        if exc_grp is None:
            raise exc
        exc_grp.append(exc)
        return None  # pyright: ignore[reportReturnType]


class LiteralMapper(MappingWorker[Literal]):  # pyright: ignore[reportMissingTypeArgument]
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[Any],
        src: SrcT,
        dest: Any | None,
        exc_grp: list[MappingError] | None,
    ) -> Any:
        values: tuple[Any, ...] = dest_t.vars
        for value in values:
            try:
                mapped_value = self.runner.map(
                    src_expr,
                    src_t,
                    dest_expr,
                    Type.from_instance(value),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                    src,
                    dest,
                    None,
                )
            except MappingError:
                continue
            if mapped_value == value:
                return value
        exc = LiteralMatchingError(src_expr, dest_expr, repr(src), values)
        if exc_grp is None:
            raise exc
        exc_grp.append(exc)


class DictMapper(MappingWorker[dict[str, Any]]):
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[dict[str, Any]],
        src: SrcT,
        dest: dict[str, Any] | None,
        exc_grp: list[MappingError] | None,
    ) -> dict[str, Any]:
        if dest is None:
            dest = dest_t.new()
        for src_name, src_value in self._iter_obj(src):
            dest[src_name] = self.runner.map(
                src_expr[src_name],
                Type.from_instance(src_value),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                getattr(dest_expr, src_name),
                Type(dest_t.vars[1]),
                src_value,
                None,
                exc_grp,
            )
        return dest

    @staticmethod
    def _iter_obj(obj: object) -> Iterable[tuple[str, Any]]:
        if isinstance(obj, dict):
            return obj.items()  # pyright: ignore[reportUnknownVariableType]
        return vars(obj).items()


class SequenceMapper(MappingWorker[list[Any] | tuple[Any, ...] | set[Any] | frozenset[Any]]):
    @override
    def map[SrcT](
        self,
        src_expr: ExpressionNode,
        src_t: Type[SrcT],
        dest_expr: ExpressionNode,
        dest_t: Type[list[Any] | tuple[Any, ...] | set[Any] | frozenset[Any]],
        src: SrcT,
        dest: list[Any] | tuple[Any, ...] | set[Any] | frozenset[Any] | None,
        exc_grp: list[MappingError] | None,
    ) -> list[Any] | tuple[Any, ...] | set[Any] | frozenset[Any]:
        elems: list[Any] = []
        if not self._is_iterable(src):
            exc = TypeNotIterableError(src_expr, dest_expr, src_t, dest_t)
            if exc_grp is None:
                raise exc
            exc_grp.append(exc)
            return None  # pyright: ignore
        for index, elem in enumerate(src):
            elems.append(
                self.runner.map(
                    src_expr[index],
                    Type.from_instance(elem),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                    dest_expr[index],
                    Type(dest_t.vars[0]),
                    elem,
                    None,
                    exc_grp,
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
            exc = ImmutableCollectionError(dest_expr)
            if exc_grp is None:
                raise exc
            exc_grp.append(exc)
            return None  # pyright: ignore
        return dest

    @staticmethod
    def _is_iterable(obj: Any) -> TypeGuard[Iterable[Any]]:
        return hasattr(obj, "__iter__")
