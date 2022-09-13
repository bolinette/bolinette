from typing import Any, Literal, Protocol

from bolinette.core import Cache, meta
from bolinette.core.utils import StringUtils
from bolinette.data import __data_cache__, types


class Reference:
    def __init__(
        self,
        entity: type[Any],
        columns: str | list[str] | None = None,
    ):
        self.entity = entity
        self.columns: list[str] | None
        if columns is not None and not isinstance(columns, list):
            self.columns = [columns]
        else:
            self.columns = columns


class Column:
    def __init__(
        self,
        data_type: types.DataType,
        reference: Reference | None = None,
        primary_key: bool = False,
        auto: bool | None = None,
        nullable: bool = False,
        unique: bool = False,
        entity_key: bool = False,
        default: Any | None = None,
    ):
        self.type = data_type
        self.auto_increment = auto
        self.reference = reference
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.entity_key = entity_key
        self.default = default


class Backref:
    def __init__(
        self,
        key: str,
        lazy: bool = True,
    ):
        self.key = key
        self.lazy = lazy


class ManyToOne:
    def __init__(
        self,
        foreign_key: Column,
        backref: Backref | None = None,
        lazy: bool | Literal["subquery"] = True,
    ):
        self.foreign_key = foreign_key
        self.backref = backref
        self.lazy = lazy


class ManyToMany:
    def __init__(
        self,
        reference: Reference,
        join_columns: Column | list[Column] | None = None,
        join_table: str | None = None,
        backref: Backref | None = None,
    ) -> None:
        self.reference = reference
        self.join_columns: list[Column] | None
        if join_columns is not None and not isinstance(join_columns, list):
            self.join_columns = [join_columns]
        else:
            self.join_columns = join_columns
        self.join_table = join_table
        self.backref = backref


class PrimaryKey:
    def __init__(self, columns: Column | list[Column]) -> None:
        self.columns: list[Column]
        if not isinstance(columns, list):
            self.columns = [columns]
        else:
            self.columns = columns


class UniqueConstraint:
    def __init__(self, columns: Column | list[Column]) -> None:
        self.columns: list[Column]
        if not isinstance(columns, list):
            self.columns = [columns]
        else:
            self.columns = columns


class ForeignKey:
    def __init__(
        self,
        source_cols: Column | list[Column],
        entity: type[Any],
        target_cols: str | list[str] | None = None,
    ) -> None:
        self.source_cols: list[Column]
        if not isinstance(source_cols, list):
            self.source_cols = [source_cols]
        else:
            self.source_cols = source_cols
        self.entity = entity
        self.target_cols: list[str] | None
        if target_cols is not None and not isinstance(target_cols, list):
            self.target_cols = [target_cols]
        else:
            self.target_cols = target_cols


class Model(Protocol):
    def __init__(self) -> None:
        pass


class ModelMeta:
    def __init__(self, entity: type[Any], table_name: str) -> None:
        self.entity = entity
        self.table_name = table_name


def model(
    entity: type[Any], /, *, table_name: str | None = None, cache: Cache | None = None
):
    def decorator(cls: type[Model]) -> type[Model]:
        meta.set(
            cls,
            ModelMeta(
                entity,
                StringUtils.to_snake_case(entity.__name__)
                if table_name is None
                else table_name,
            ),
        )
        (cache or __data_cache__).add(ModelMeta, cls)
        return cls

    return decorator
