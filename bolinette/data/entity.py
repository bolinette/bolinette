from collections.abc import Callable
from typing import Literal, Protocol, TypeVar, overload

from bolinette.core import Cache, meta
from bolinette.core.utils import StringUtils
from bolinette.data import __data_cache__


class Entity(Protocol):
    def __init__(self) -> None:
        pass


class _ColumnProps:
    class ForeignKey:
        def __init__(
            self,
            name: str | None,
            target: type[Entity] | None,
            target_cols: list[str] | None,
            reference: str | None,
        ) -> None:
            self.name = name
            self.target = target
            self.target_cols = target_cols
            self.reference = reference

    def __init__(
        self,
        name: str,
        primary: tuple[str | None, bool],
        format: Literal["password", "email"] | None,
        unique: tuple[str | None, bool],
        foreign_key: ForeignKey | None,
    ) -> None:
        self.name = name
        self.primary = primary
        self.format = format
        self.unique = unique
        self.foreign_key = foreign_key


class EntityMeta:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name


class EntityPropsMeta:
    class ForeignKeyTempDef:
        def __init__(
            self,
            name: str | None,
            src_cols: list[str],
            reference: str | None,
            target: type[Entity] | None,
            target_cols: list[str] | None,
        ) -> None:
            self.name = name
            self.src_cols = src_cols
            self.reference = reference
            self.target = target
            self.target_cols = target_cols

    def __init__(self) -> None:
        self.primary_key: tuple[str | None, list[str]] = (None, [])
        self.unique_constraints: list[tuple[str | None, list[str]]] = []
        self.foreign_keys: list[EntityPropsMeta.ForeignKeyTempDef] = []
        self.columns: dict[str, _ColumnProps] = {}


_EntityT = TypeVar("_EntityT", bound=Entity)


class _EntityColumnDecorator:
    def __init__(self, name: str) -> None:
        self.name = name
        self._primary_key: tuple[str | None, bool] = (None, False)
        self._format: Literal["password", "email"] | None = None
        self._unique: tuple[str | None, bool] = (None, False)
        self._foreign_key: _ColumnProps.ForeignKey | None = None

    def _get_meta(self, cls: type[_EntityT]) -> EntityPropsMeta:
        if meta.has(cls, EntityPropsMeta):
            _meta = meta.get(cls, EntityPropsMeta)
        else:
            _meta = EntityPropsMeta()
            meta.set(cls, _meta)
        return _meta

    def __call__(self, cls: type[_EntityT]) -> type[_EntityT]:
        _meta = self._get_meta(cls)
        _meta.columns[self.name] = _ColumnProps(
            self.name, self._primary_key, self._format, self._unique, self._foreign_key
        )
        return cls

    def format(
        self, value: Literal["password", "email"] | None, /
    ) -> "_EntityColumnDecorator":
        self._format = value
        return self

    def unique(
        self, value: bool = True, /, *, name: str | None = None
    ) -> "_EntityColumnDecorator":
        self._unique = (name, value)
        return self

    @overload
    def many_to_one(
        self,
        *,
        target: type[Entity],
        target_columns: str | list[str] | None = None,
        name: str | None = None,
    ) -> "_EntityColumnDecorator":
        pass

    @overload
    def many_to_one(
        self,
        *,
        reference: str,
        target_columns: str | list[str] | None = None,
        name: str | None = None,
    ) -> "_EntityColumnDecorator":
        pass

    def many_to_one(
        self,
        *,
        target: type[Entity] | None = None,
        reference: str | None = None,
        target_columns: str | list[str] | None = None,
        name: str | None = None,
    ) -> "_EntityColumnDecorator":
        _target_cols: list[str] | None
        if target_columns is not None and not isinstance(target_columns, list):
            _target_cols = [target_columns]
        else:
            _target_cols = target_columns
        self._foreign_key = _ColumnProps.ForeignKey(
            name, target, _target_cols, reference
        )
        return self

    def primary_key(
        self, value: bool = True, /, *, name: str | None = None
    ) -> "_EntityColumnDecorator":
        self._primary_key = (name, value)
        return self


class _EntityDecorator:
    def _get_meta(self, cls: type[_EntityT]) -> EntityPropsMeta:
        if meta.has(cls, EntityPropsMeta):
            _meta = meta.get(cls, EntityPropsMeta)
        else:
            _meta = EntityPropsMeta()
            meta.set(cls, _meta)
        return _meta

    def __call__(self, *, table_name: str | None = None, cache: Cache | None = None):
        def decorator(cls: type[_EntityT]) -> type[_EntityT]:
            meta.set(
                cls,
                EntityMeta(
                    table_name
                    if table_name
                    else StringUtils.to_snake_case(cls.__name__)
                ),
            )
            (cache or __data_cache__).add(EntityMeta, cls)
            if not meta.has(cls, EntityPropsMeta):
                meta.set(cls, EntityPropsMeta())
            return cls

        return decorator

    def column(self, name: str, /):
        return _EntityColumnDecorator(name)

    def primary_key(self, column: str, /, *columns: str, name: str | None = None):
        def decorator(cls: type[_EntityT]) -> type[_EntityT]:
            _meta = self._get_meta(cls)
            _meta.primary_key = (name, [column, *columns])
            return cls

        return decorator

    def unique(self, column: str, /, *columns: str, name: str | None = None):
        def decorator(cls: type[_EntityT]) -> type[_EntityT]:
            _meta = self._get_meta(cls)
            _meta.unique_constraints.append((name, [column, *columns]))
            return cls

        return decorator

    @overload
    def many_to_one(
        self,
        source_column: str,
        /,
        *source_columns: str,
        reference: str,
        target_columns: str | list[str] | None = None,
        name: str | None = None,
    ) -> Callable[[type[_EntityT]], type[_EntityT]]:
        pass

    @overload
    def many_to_one(
        self,
        source_column: str,
        /,
        *source_columns: str,
        target: type[Entity],
        target_columns: str | list[str] | None = None,
        name: str | None = None,
    ) -> Callable[[type[_EntityT]], type[_EntityT]]:
        pass

    def many_to_one(
        self,
        source_column: str,
        /,
        *source_columns: str,
        reference: str | None = None,
        target: type[Entity] | None = None,
        target_columns: str | list[str] | None = None,
        name: str | None = None,
    ) -> Callable[[type[_EntityT]], type[_EntityT]]:
        def decorator(cls: type[_EntityT]) -> type[_EntityT]:
            _meta = self._get_meta(cls)
            _src_cols = [source_column, *source_columns]
            _tgt_cols: list[str] | None
            if target_columns is not None and not isinstance(target_columns, list):
                _tgt_cols = [target_columns]
            else:
                _tgt_cols = target_columns
            _meta.foreign_keys.append(
                EntityPropsMeta.ForeignKeyTempDef(
                    name, _src_cols, reference, target, _tgt_cols
                )
            )
            return cls

        return decorator


entity = _EntityDecorator()
