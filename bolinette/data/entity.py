from typing import Literal, Protocol, TypeVar

from bolinette.core import Cache, meta
from bolinette.core.utils import StringUtils
from bolinette.data import __data_cache__


class _ColumnProps:
    def __init__(
        self,
        name: str,
        format: Literal["password", "email"] | None,
        unique: tuple[str | None, bool],
    ) -> None:
        self.name = name
        self.format = format
        self.unique = unique


class EntityMeta:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name


class EntityPropsMeta:
    def __init__(self) -> None:
        self.primary_key: tuple[str | None, list[str]] = (None, [])
        self.unique_constraints: list[tuple[str | None, list[str]]] = []
        self.columns: dict[str, _ColumnProps] = {}


class Entity(Protocol):
    def __init__(self) -> None:
        pass


_EntityT = TypeVar("_EntityT", bound=Entity)


class _EntityColumnDecorator:
    def __init__(self, name: str) -> None:
        self.name = name
        self._format: Literal["password", "email"] | None = None
        self._unique: tuple[str | None, bool] = (None, False)

    def _get_meta(self, cls: type[_EntityT]) -> EntityPropsMeta:
        if meta.has(cls, EntityPropsMeta):
            _meta = meta.get(cls, EntityPropsMeta)
        else:
            _meta = EntityPropsMeta()
            meta.set(cls, _meta)
        return _meta

    def __call__(self, cls: type[_EntityT]) -> type[_EntityT]:
        _meta = self._get_meta(cls)
        _meta.columns[self.name] = _ColumnProps(self.name, self._format, self._unique)
        return cls

    def format(
        self, value: Literal["password", "email"] | None
    ) -> "_EntityColumnDecorator":
        self._format = value
        return self

    def unique(
        self, value: bool = True, *, name: str | None = None
    ) -> "_EntityColumnDecorator":
        self._unique = (name, value)
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

    def column(self, name: str):
        return _EntityColumnDecorator(name)

    def primary_key(self, column: str, *columns: str, name: str | None = None):
        def decorator(cls: type[_EntityT]) -> type[_EntityT]:
            _meta = self._get_meta(cls)
            _meta.primary_key = (name, [column, *columns])
            return cls

        return decorator

    def unique(self, column: str, *columns: str, name: str | None = None):
        def decorator(cls: type[_EntityT]) -> type[_EntityT]:
            _meta = self._get_meta(cls)
            _meta.unique_constraints.append((name, [column, *columns]))
            return cls

        return decorator


entity = _EntityDecorator()
