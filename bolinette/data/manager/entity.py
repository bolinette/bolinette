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
    Entity,
    ForeignKey,
    Format,
    ManyToOne,
    OneToMany,
    PrimaryKey,
    Unique,
    __data_cache__,
    types,
)
from bolinette.data.entity import EntityMeta
from bolinette.data.exceptions import EntityError
from bolinette.data.manager import (
    CollectionReference,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    TableColumn,
    TableDefinition,
    TableReference,
    UniqueConstraint,
)


@injectable(cache=__data_cache__)
class EntityManager:
    def __init__(
        self, cache: Cache, attrs: AttributeUtils, logger: "Logger[EntityManager]"
    ) -> None:
        self._cache = cache
        self._attrs = attrs
        self._logger = logger
        self._table_defs: dict[type[Entity], TableDefinition] = {}

    @staticmethod
    def check_columns_match(
        cols1: "list[TableColumn]", cols2: "list[TableColumn]"
    ) -> bool:
        if len(cols1) != len(cols2):
            return False
        for i in range(len(cols1)):
            col1 = cols1[i]
            col2 = cols2[i]
            if col1.py_type is not col2.py_type:
                return False
        return True

    @init_method
    def init(self) -> None:
        self._init_models()
        temp_defs: dict[type[Entity], TempTableDef] = dict(
            (
                (entity, TempTableDef(table_def.name))
                for entity, table_def in self._table_defs.items()
            )
        )
        self._parse_annotations(temp_defs)
        self._parse_constraints(temp_defs)
        self._populate_tables(temp_defs)
        self._populate_references(temp_defs)
        self._populate_constraints(temp_defs)
        self._populate_back_references(temp_defs)

    def _init_models(self) -> None:
        _type = type[Entity]
        for cls in self._cache[EntityMeta, _type]:
            entity_meta = meta.get(cls, EntityMeta)
            table_def = TableDefinition(entity_meta.table_name, cls)
            self._table_defs[cls] = table_def

    @staticmethod
    def _parse_annotations(temp_defs: "dict[type[Entity], TempTableDef]") -> None:
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
                if types.is_supported(h_type):
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
                                    TempUnique(
                                        h_name,
                                        anno_arg.name or f"{tmp_def.name}_{h_name}_u",
                                        [h_name],
                                    )
                                )
                            elif isinstance(anno_arg, PrimaryKey):
                                tmp_def.primary_keys.append(
                                    TempPrimaryKey(
                                        h_name,
                                        anno_arg.name or f"{tmp_def.name}_{h_name}_pk",
                                        [h_name],
                                    )
                                )
                            elif isinstance(anno_arg, ForeignKey):
                                tmp_def.foreign_keys.append(
                                    TempForeignKey(
                                        h_name,
                                        anno_arg.name,
                                        [h_name],
                                        anno_arg.target,
                                    )
                                )
                    tmp_def.columns.append(TempColumn(h_name, h_type, nullable, format))
                elif h_type in temp_defs:
                    for anno_arg in anno_args:
                        if isinstance(anno_arg, ManyToOne):
                            if is_collection:
                                raise EntityError(
                                    f"Many-to-one relationship must be a single reference",
                                    entity=entity,
                                    attribute=h_name,
                                )
                            tmp_def.many_to_ones.append(
                                TempManyToOne(
                                    h_name,
                                    h_name,
                                    h_type,  # type: ignore
                                    anno_arg.lazy,  # type: ignore
                                    anno_arg.columns,
                                    anno_arg.other_side,
                                )
                            )
                            break
                        if isinstance(anno_arg, OneToMany):
                            if not is_collection:
                                raise EntityError(
                                    f"One-to-many relationship must be a collection reference",
                                    entity=entity,
                                    attribute=h_name,
                                )
                            tmp_def.one_to_manies.append(
                                TempOneToMany(
                                    h_name,
                                    h_name,
                                    h_type,  # type: ignore
                                    anno_arg.lazy,  # type: ignore
                                    anno_arg.columns,
                                    anno_arg.other_side,
                                )
                            )
                            break
                    else:
                        raise EntityError(
                            f"Reference to {h_type} does not define any relationship",
                            entity=entity,
                            attribute=h_name,
                        )
                else:
                    raise EntityError(
                        f"Type {h_type} is not supported",
                        entity=entity,
                        attribute=h_name,
                    )

    def _parse_constraints(self, temp_defs: "dict[type[Entity], TempTableDef]") -> None:
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
                    tmp_def.uniques.append(TempUnique(c_name, c_name, const.columns))
                elif isinstance(const, PrimaryKey):
                    tmp_def.primary_keys.append(
                        TempPrimaryKey(c_name, c_name, const.columns)
                    )
                elif isinstance(const, ForeignKey):
                    tmp_def.foreign_keys.append(
                        TempForeignKey(c_name, c_name, const.columns, const.target)
                    )

    def _populate_tables(self, temp_defs: "dict[type[Entity], TempTableDef]"):
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
                    table_def, tmp_unique.name, u_columns
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
                    table_def, tmp_primary.name, pk_columns
                )
            # == Check if there is only one primary key ==
            primary_keys = table_def.get_constraints(PrimaryKeyConstraint)
            if len(primary_keys) == 0:
                raise EntityError(f"No primary keys have been defined", entity=entity)
            elif len(primary_keys) > 1:
                raise EntityError(
                    f"Several primary keys have been defined", entity=entity
                )

        # == Add Foreign Key Constraints ==
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
                source_cols: list[TableColumn] = []
                for col_name in tmp_fk.source_cols:
                    source_cols.append(table_def.columns[col_name])
                target_cols = list(target_table.get_primary_key().columns)
                if not self.check_columns_match(source_cols, target_cols):
                    raise EntityError(
                        f"Source columns in foreign key do not match with target columns",
                        entity=entity,
                        attribute=tmp_fk.origin_name,
                    )
                table_def.constraints[fk_name] = ForeignKeyConstraint(
                    table_def, fk_name, source_cols, target_table, target_cols
                )

    def _populate_references(
        self, temp_defs: "dict[type[Entity], TempTableDef]"
    ) -> None:
        for entity, tmp_def in temp_defs.items():
            table_def = self._table_defs[entity]
            for tmp_mto in tmp_def.many_to_ones:
                target_def = self._table_defs[tmp_mto.type]
                reference = TableReference(
                    table_def,
                    tmp_mto.name,
                    target_def,
                    tmp_mto.lazy,  # type: ignore
                )
                table_def.references[reference.name] = reference
            for tmp_otm in tmp_def.one_to_manies:
                target_def = self._table_defs[tmp_otm.type]
                collection = CollectionReference(
                    table_def,
                    tmp_otm.name,
                    target_def,
                    tmp_otm.lazy,  # type: ignore
                )
                table_def.references[collection.name] = collection

    def _populate_constraints(
        self, temp_defs: "dict[type[Entity], TempTableDef]"
    ) -> None:
        def _create_const(
            _origin_name: str,
            _column_names: list[str],
            _ref: TableReference | CollectionReference,
            _from: TableDefinition,
            _to: TableDefinition,
        ):
            columns: list[TableColumn] = []
            for col_name in _column_names:
                if col_name not in _from.columns:
                    raise EntityError(
                        f"Column '{col_name}' does not exist in entity",
                        entity=entity,
                        attribute=_origin_name,
                    )
                columns.append(_from.columns[col_name])
            const = _from.find_constraint(columns)
            if const is None or not isinstance(const, ForeignKeyConstraint):
                raise EntityError(
                    f"Columns defined in reference do not match with any foreign key",
                    entity=entity,
                    attribute=_origin_name,
                )
            if const.target != _to:
                raise EntityError(
                    f"Reference type is not the same as foreign key target entity",
                    entity=entity,
                    attribute=_origin_name,
                )
            if isinstance(_ref, TableReference):
                const.reference = _ref
            else:
                const.backref = _ref

        for entity, tmp_def in temp_defs.items():
            table_def = self._table_defs[entity]
            for tmp_mto in tmp_def.many_to_ones:
                reference = table_def.references[tmp_mto.name]
                assert isinstance(reference, TableReference)
                _create_const(
                    tmp_mto.origin_name,
                    tmp_mto.columns,
                    reference,
                    table_def,
                    reference.target,
                )
            for tmp_otm in tmp_def.one_to_manies:
                collection = table_def.references[tmp_otm.name]
                assert isinstance(collection, CollectionReference)
                _create_const(
                    tmp_otm.origin_name,
                    tmp_otm.columns,
                    collection,
                    collection.target,
                    table_def,
                )

    def _populate_back_references(
        self, temp_defs: "dict[type[Entity], TempTableDef]"
    ) -> None:
        for entity, tmp_def in temp_defs.items():
            table_def = self._table_defs[entity]
            # == Add Many-To-One Back Relationships ==
            for tmp_mto in tmp_def.many_to_ones:
                column_def = table_def.references[tmp_mto.name]
                assert isinstance(column_def, TableReference)
                target_def = self._table_defs[tmp_mto.type]
                other_side: TableReference | CollectionReference | None = None
                other_side_name = tmp_mto.other_side
                if other_side_name is not None:
                    if other_side_name not in target_def.references:
                        raise EntityError(
                            f"Relationship '{other_side_name}' does not exist on type {target_def.entity}",
                            entity=entity,
                            attribute=tmp_mto.origin_name,
                        )
                    other_side = target_def.references[other_side_name]
                    if not isinstance(other_side, CollectionReference):
                        raise EntityError(
                            f"Relationship '{other_side_name}' must be a collection reference",
                            entity=entity,
                            attribute=tmp_mto.origin_name,
                        )
                    column_def.other_side = other_side
                else:
                    column_def.other_side = None

            # == Add One-To-Many Back Relationships ==
            for tmp_otm in tmp_def.one_to_manies:
                column_def = table_def.references[tmp_otm.name]
                assert isinstance(column_def, CollectionReference)
                target_def = self._table_defs[tmp_otm.type]
                other_side_name = tmp_otm.other_side
                if other_side_name is not None:
                    if other_side_name not in target_def.references:
                        raise EntityError(
                            f"Relationship '{other_side_name}' does not exist on type {target_def.entity}",
                            entity=entity,
                            attribute=tmp_otm.origin_name,
                        )
                    other_side = target_def.references[other_side_name]
                    if not isinstance(other_side, TableReference):
                        raise EntityError(
                            f"Relationship '{other_side_name}' must be a single reference",
                            entity=entity,
                            attribute=tmp_otm.origin_name,
                        )
                    column_def.other_side = other_side
                else:
                    column_def.other_side = None


EntityT = TypeVar("EntityT", bound=Entity)


class TempTableDef(Generic[EntityT]):
    def __init__(self, name: str) -> None:
        self.name = name
        self.columns: list[TempColumn] = []
        self.foreign_keys: list[TempForeignKey] = []
        self.primary_keys: list[TempPrimaryKey] = []
        self.uniques: list[TempUnique] = []
        self.many_to_ones: list[TempManyToOne] = []
        self.one_to_manies: list[TempOneToMany] = []


class TempColumn:
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


class TempForeignKey:
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


class TempPrimaryKey:
    def __init__(self, origin_name: str, name: str, columns: list[str], /) -> None:
        self.origin_name = origin_name
        self.name = name
        self.columns = columns


class TempUnique:
    def __init__(self, origin_name: str, name: str, columns: list[str], /) -> None:
        self.origin_name = origin_name
        self.name = name
        self.columns = columns


class TempManyToOne:
    def __init__(
        self,
        origin_name: str,
        name: str,
        _type: type[Entity],
        lazy: bool | Literal["subquery"],
        columns: list[str],
        other_side: str | None,
        /,
    ) -> None:
        self.origin_name = origin_name
        self.name = name
        self.type = _type
        self.lazy = lazy
        self.columns = columns
        self.other_side = other_side


class TempOneToMany:
    def __init__(
        self,
        origin_name: str,
        name: str,
        _type: type[Entity],
        lazy: bool | Literal["subquery"],
        columns: list[str],
        other_side: str | None,
        /,
    ) -> None:
        self.origin_name = origin_name
        self.name = name
        self.type = _type
        self.lazy = lazy
        self.columns = columns
        self.other_side = other_side
