from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

from sqlalchemy import table

from bolinette.core import Cache, Logger, init_method, injectable, meta
from bolinette.core.utils import AttributeUtils
from bolinette.data import (
    DataSection,
    ForeignKey,
    Format,
    PrimaryKey,
    Unique,
    __data_cache__,
    types,
)
from bolinette.data.entity import Entity, EntityMeta
from bolinette.data.exceptions import EntityError


@injectable(cache=__data_cache__)
class DatabaseManager:
    def __init__(self, section: DataSection, entities: "EntityManager") -> None:
        self._section = section
        self._entities = entities


@injectable(cache=__data_cache__)
class EntityManager:
    def __init__(
        self, cache: Cache, attrs: AttributeUtils, logger: "Logger[EntityManager]"
    ) -> None:
        self._cache = cache
        self._attrs = attrs
        self._logger = logger
        self._table_defs: dict[type[Entity], TableDefinition] = {}

    @init_method
    def init(self) -> None:
        self._init_models()
        temp_defs: dict[type[Entity], _TempTableDef] = dict(
            (
                (entity, _TempTableDef(table_def.name))
                for entity, table_def in self._table_defs.items()
            )
        )
        self._parse_annotations(temp_defs)
        self._parse_constraints(temp_defs)
        self._populate_tables(temp_defs)

    def _init_models(self) -> None:
        _type = type[Entity]
        for cls in self._cache[EntityMeta, _type]:
            entity_meta = meta.get(cls, EntityMeta)
            table_def = TableDefinition(entity_meta.table_name, cls)
            self._table_defs[cls] = table_def

    @staticmethod
    def _parse_annotations(temp_defs: "dict[type[Entity], _TempTableDef]") -> None:
        for entity, tmp_def in temp_defs.items():
            hints: dict[str, type] = get_type_hints(entity, include_extras=True)
            h_type: type
            for h_name, h_type in hints.items():
                is_collection = False
                anno_args: list[Any] = []
                nullable = False
                origin: type | None = get_origin(h_type)
                if origin is Annotated:
                    h_type, *anno_args = get_args(h_type)
                origin = get_origin(h_type)
                if origin is not None:
                    h_args: tuple[type, ...] = get_args(h_type)
                    if origin is UnionType:
                        nullable = NoneType in h_args
                        h_args = tuple(a for a in h_args if a is not NoneType)
                        if len(h_args) > 1:
                            raise EntityError(
                                "Union types are not allowed",
                                entity=entity,
                                attribute=h_name,
                            )
                        h_type = h_args[0]
                    elif origin is list:
                        is_collection = True
                        h_type = h_args[0]
                if is_collection:
                    target_ent = h_type
                    if target_ent not in temp_defs:
                        raise EntityError(
                            f"Type {target_ent} is not a registered entity",
                            entity=entity,
                            attribute=h_name,
                        )
                    tmp_def.collections.append(
                        _TempTableDef.Collection(h_name, target_ent)
                    )
                elif types.is_supported(h_type):
                    format: Literal["password", "email"] | None = None
                    for anno_arg in anno_args:
                        if isinstance(anno_arg, Format):
                            format = anno_arg.format  # type: ignore
                            continue
                        elif isinstance(anno_arg, (Unique, PrimaryKey, ForeignKey)):
                            if anno_arg.columns is not None:
                                raise EntityError(
                                    f"Annotated {anno_arg.__lower_name__} must not provide columns",
                                    entity=entity,
                                    attribute=h_name,
                                )
                            if isinstance(anno_arg, Unique):
                                tmp_def.uniques.append(
                                    _TempTableDef.Unique(
                                        h_name,
                                        anno_arg.name or f"{tmp_def.name}_{h_name}_u",
                                        [h_name],
                                    )
                                )
                            elif isinstance(anno_arg, PrimaryKey):
                                tmp_def.primary_keys.append(
                                    _TempTableDef.PrimaryKey(
                                        h_name,
                                        anno_arg.name or f"{tmp_def.name}_{h_name}_pk",
                                        [h_name],
                                    )
                                )
                            elif isinstance(anno_arg, ForeignKey):
                                tmp_def.foreign_keys.append(
                                    _TempTableDef.ForeignKey(
                                        h_name,
                                        anno_arg.name,
                                        [h_name],
                                        anno_arg.target,
                                    )
                                )
                    tmp_def.columns.append(
                        _TempTableDef.Column(h_name, h_type, nullable, format)
                    )
                elif h_type in temp_defs:
                    pass
                    # tmp_def.many_to_ones.append(_TempTableDef.ManyToOne(h_name, h_type))
                else:
                    raise EntityError(
                        f"Type {h_type} is not supported",
                        entity=entity,
                        attribute=h_name,
                    )

    def _parse_constraints(
        self, temp_defs: "dict[type[Entity], _TempTableDef]"
    ) -> None:
        for entity, tmp_def in temp_defs.items():
            for c_name, const in self._attrs.get_cls_attrs(
                entity, of_type=(Unique, PrimaryKey, ForeignKey)
            ):
                if const.name is not None:
                    raise EntityError(
                        f"Class level {const.__lower_name__} must not define a custom name",
                        entity=entity,
                        attribute=c_name,
                    )
                if not const.columns:
                    raise EntityError(
                        f"Class level {const.__lower_name__} must provide columns",
                        entity=entity,
                        attribute=c_name,
                    )
                if isinstance(const, Unique):
                    tmp_def.uniques.append(
                        _TempTableDef.Unique(c_name, c_name, const.columns)
                    )
                elif isinstance(const, PrimaryKey):
                    tmp_def.primary_keys.append(
                        _TempTableDef.PrimaryKey(c_name, c_name, const.columns)
                    )
                elif isinstance(const, ForeignKey):
                    tmp_def.foreign_keys.append(
                        _TempTableDef.ForeignKey(
                            c_name, c_name, const.columns, const.target
                        )
                    )

    def _populate_tables(self, temp_defs: "dict[type[Entity], _TempTableDef]"):
        # == Add Table Columns ==
        for entity, tmp_def in temp_defs.items():
            table_def = self._table_defs[entity]
            for tmp_col in tmp_def.columns:
                table_def.columns[tmp_col.name] = TableColumn(
                    table_def,
                    tmp_col.name,
                    tmp_col.type,
                    types.get_sql_type(tmp_col.type),
                    tmp_col.nullable,
                    tmp_col.format,  # type: ignore
                )

        # == Add Unique Constraints ==
        for entity, tmp_def in temp_defs.items():
            table_def = self._table_defs[entity]
            for tmp_unique in tmp_def.uniques:
                u_columns: list[TableColumn] = []
                for col_name in tmp_unique.columns:
                    if col_name not in table_def.columns:
                        raise EntityError(
                            f"Unique constraint does not reference a valid column '{col_name}'",
                            entity=entity,
                            attribute=tmp_unique.origin_name,
                        )
                    u_columns.append(table_def.columns[col_name])
                if existing_u := table_def.check_unique(u_columns):
                    raise EntityError(
                        f"A similar unique constraint has already been defined by '{existing_u.name}'",
                        entity=entity,
                        attribute=tmp_unique.origin_name,
                    )
                table_def.constraints[tmp_unique.name] = UniqueConstraint(
                    tmp_unique.name, u_columns
                )

        # == Add Primary Key Constraints ==
        for entity, tmp_def in temp_defs.items():
            table_def = self._table_defs[entity]
            for tmp_primary in tmp_def.primary_keys:
                pk_columns: list[TableColumn] = []
                for col_name in tmp_primary.columns:
                    if col_name not in table_def.columns:
                        raise EntityError(
                            f"Primary key does not reference a valid column '{col_name}'",
                            entity=entity,
                            attribute=tmp_primary.origin_name,
                        )
                    pk_columns.append(table_def.columns[col_name])
                if existing_u := table_def.check_unique(pk_columns):
                    raise EntityError(
                        f"A unique constraint has already been defined by '{existing_u.name}'",
                        entity=entity,
                        attribute=tmp_primary.origin_name,
                    )
                table_def.constraints[tmp_primary.name] = PrimaryKeyConstraint(
                    tmp_primary.name, pk_columns
                )
            # == Check if there is only one primary key ==
            primary_keys = table_def.get_constraints(PrimaryKeyConstraint)
            if len(primary_keys) == 0:
                raise EntityError(f"No primary keys have been defined", entity=entity)
            elif len(primary_keys) > 1:
                raise EntityError(
                    f"Several primary keys have been defined", entity=entity
                )

        # == Add Foreign Key Constraints
        for entity, tmp_def in temp_defs.items():
            table_def = self._table_defs[entity]
            for tmp_fk in tmp_def.foreign_keys:
                target_type = tmp_fk.target
                if target_type not in self._table_defs:
                    raise EntityError(
                        f"Type {target_type} is not a registered entity",
                        entity=entity,
                        attribute=tmp_fk.origin_name,
                    )
                target_table = self._table_defs[target_type]
                if (fk_name := tmp_fk.name) is None:
                    fk_name = f"{table_def.name}_{target_table.name}_fk"
                source_cols = list(table_def.get_primary_key().columns)
                target_cols = list(target_table.get_primary_key().columns)
                table_def.constraints[fk_name] = ForeignKeyConstraint(
                    fk_name, source_cols, target_table, target_cols
                )


class TableColumn:
    def __init__(
        self,
        table: "TableDefinition",
        name: str,
        py_type: type,
        sql_type,
        nullable: bool,
        format: Literal["password", "email"] | None,
    ) -> None:
        self.table = table
        self.name = name
        self.py_type = py_type
        self.sql_type = sql_type
        self.nullable = nullable
        self.format = format


class TableReference:
    def __init__(
        self,
        table: "TableDefinition",
        name: str,
        target: "TableDefinition",
    ) -> None:
        self.table = table
        self.name = name
        self.target = target
        self.lazy: bool | Literal["subquery"] = True
        self.constraint: ForeignKeyConstraint | None = None
        self.other_side: CollectionReference | TableReference | None = None


class CollectionReference:
    def __init__(
        self,
        table: "TableDefinition",
        name: str,
        element: "TableDefinition",
    ) -> None:
        self.table = table
        self.name = name
        self.element = element
        self.lazy: bool | Literal["subquery"] = True
        self.constraint: ForeignKeyConstraint | None = None
        self.other_side: CollectionReference | TableReference | None = None


class PrimaryKeyConstraint:
    def __init__(self, name: str, columns: list[TableColumn]) -> None:
        self.name = name
        self.columns = columns


class ForeignKeyConstraint:
    def __init__(
        self,
        name: str,
        source_columns: list[TableColumn],
        target: "TableDefinition",
        target_columns: list[TableColumn],
    ) -> None:
        self.name = name
        self.source_columns = source_columns
        self.target = target
        self.target_columns = target_columns
        self.reference: TableReference | None = None


class UniqueConstraint:
    def __init__(self, name: str, columns: list[TableColumn]) -> None:
        self.name = name
        self.columns = columns


EntityT = TypeVar("EntityT", bound=Entity)
ConstraintType = UniqueConstraint | PrimaryKeyConstraint | ForeignKeyConstraint
ConstraintT = TypeVar("ConstraintT", bound=ConstraintType)


class TableDefinition(Generic[EntityT]):
    def __init__(self, name: str, entity: type[EntityT]) -> None:
        self.name = name
        self.entity = entity
        self.columns: dict[str, TableColumn] = {}
        self.references: dict[str, TableReference | CollectionReference] = {}
        self.constraints: dict[str, ConstraintType] = {}

    def get_constraints(
        self,
        of_type: type[ConstraintT],
    ) -> list[tuple[str, ConstraintT]]:
        return [(n, a) for n, a in self.constraints.items() if isinstance(a, of_type)]

    def get_primary_key(self) -> PrimaryKeyConstraint:
        return next(
            c for c in self.constraints.values() if isinstance(c, PrimaryKeyConstraint)
        )

    def check_unique(self, columns: list[TableColumn]) -> UniqueConstraint | None:
        for constraint in {a for _, a in self.get_constraints(UniqueConstraint)}:
            for col_def in constraint.columns:
                if col_def not in columns:
                    break
            else:
                return constraint
        return None


class _TempTableDef(Generic[EntityT]):
    class Column:
        def __init__(
            self,
            name: str,
            _type: type,
            nullable: bool,
            format: Literal["email", "password"] | None,
            /,
        ) -> None:
            self.name = name
            self.type = _type
            self.nullable = nullable
            self.format = format

    class ForeignKey:
        def __init__(
            self,
            origin_name: str,
            name: str | None,
            source_cols: list[str],
            target: type[Entity],
            /,
        ) -> None:
            self.origin_name = origin_name
            self.name = name
            self.source_cols = source_cols
            self.target = target

    class Collection:
        def __init__(self, name: str, _type: type, /) -> None:
            self.name = name
            self.type = _type

    class PrimaryKey:
        def __init__(self, origin_name: str, name: str, columns: list[str], /) -> None:
            self.origin_name = origin_name
            self.name = name
            self.columns = columns

    class Unique:
        def __init__(self, origin_name: str, name: str, columns: list[str], /) -> None:
            self.origin_name = origin_name
            self.name = name
            self.columns = columns

    def __init__(self, name: str) -> None:
        self.name = name
        self.columns: list[_TempTableDef.Column] = []
        self.foreign_keys: list[_TempTableDef.ForeignKey] = []
        self.collections: list[_TempTableDef.Collection] = []
        self.primary_keys: list[_TempTableDef.PrimaryKey] = []
        self.uniques: list[_TempTableDef.Unique] = []
