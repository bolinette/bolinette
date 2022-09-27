from types import NoneType, UnionType
from typing import Generic, Literal, TypeVar, get_args, get_origin, get_type_hints

from sqlalchemy import table

from bolinette.core import Cache, Logger, init_method, injectable, meta
from bolinette.core.utils import AttributeUtils
from bolinette.data import DataSection, __data_cache__, types
from bolinette.data.entity import Entity, EntityMeta, EntityPropsMeta
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
        self._table_defs: dict[type, TableDefinition] = {}

    @init_method
    def init(self) -> None:
        self._init_models()
        self._init_columns()
        self._init_unique_constraints()
        self._init_primary_key()
        self._init_many_to_ones()
        self._init_many_to_manies()

    def _init_models(self) -> None:
        _type = type[Entity]
        for cls in self._cache[EntityMeta, _type]:
            entity_meta = meta.get(cls, EntityMeta)
            table_def = TableDefinition(entity_meta.table_name, cls)
            self._table_defs[cls] = table_def

    def _init_columns(self) -> None:
        for table_def in self._table_defs.values():
            hints: dict[str, type] = get_type_hints(table_def.entity)
            all_col_defs: dict[str, TableColumn] = {}
            for h_name, h_type in hints.items():
                is_collection = False
                nullable = False
                origin: type | None
                if (origin := get_origin(h_type)) is not None:
                    h_args: tuple[type, ...] = get_args(h_type)
                    if origin is UnionType:
                        nullable = NoneType in h_args
                        h_args = tuple(a for a in h_args if a is not NoneType)
                        if len(h_args) > 1:
                            raise EntityError(
                                "Union types are not allowed",
                                entity=table_def.entity,
                                attribute=h_name,
                            )
                        h_type = h_args[0]
                    elif origin is list:
                        is_collection = True
                        h_type = h_args[0]
                if is_collection:
                    target_ent = h_type
                    if target_ent not in self._table_defs:
                        raise EntityError(
                            f"Type {target_ent} is not a registered entity",
                            entity=table_def.entity,
                            attribute=h_name,
                        )
                    collection_def = CollectionReference(
                        table_def, h_name, self._table_defs[target_ent]
                    )
                    table_def.references[h_name] = collection_def
                elif types.is_supported(h_type):
                    _meta = meta.get(table_def.entity, EntityPropsMeta)
                    format: Literal["password", "email"] | None
                    if h_name in _meta.columns:
                        format = _meta.columns[h_name].format  # type: ignore
                    else:
                        format = None
                    col_def = TableColumn(
                        table_def,
                        h_name,
                        h_type,
                        types.get_sql_type(h_type),
                        nullable,
                        format,
                    )
                    table_def.columns[h_name] = col_def
                    all_col_defs[h_name] = col_def
                elif h_type in self._table_defs:
                    ref_def = TableReference(
                        table_def, h_name, self._table_defs[h_type]
                    )
                    table_def.references[h_name] = ref_def
                else:
                    raise EntityError(
                        f"Type {h_type} is not supported",
                        entity=table_def.entity,
                        attribute=h_name,
                    )
            _meta = meta.get(table_def.entity, EntityPropsMeta)
            for col_name in _meta.columns:
                if col_name not in all_col_defs:
                    raise EntityError(
                        f"'{col_name}' in entity decorator does not match with any column",
                        entity=table_def.entity,
                    )

    def _init_unique_constraints(self) -> None:
        for table_def in self._table_defs.values():
            _meta = meta.get(table_def.entity, EntityPropsMeta)
            unique_defs: list[tuple[str | None, list[TableColumn]]] = []
            for c_name, key in _meta.unique_constraints:
                for att_name in key:
                    if att_name not in table_def.columns:
                        raise EntityError(
                            f"'{att_name}' in unique constraint does not refer to an entity column",
                            entity=table_def.entity,
                        )
                unique_defs.append(
                    (c_name, list(map(lambda k: table_def.columns[k], key)))
                )
            for col_name, col_def in _meta.columns.items():
                if col_def.unique[1]:
                    unique_defs.append(
                        (col_def.unique[0], [table_def.columns[col_name]])
                    )
            for c_name, col_defs in unique_defs:
                if c_name is None:
                    c_name = f"{table_def.name}_{'_'.join(map(lambda c: c.name, col_defs))}_u"
                constraint = UniqueConstraint(c_name, col_defs)
                if table_def.check_unique(constraint.columns):
                    raise EntityError(
                        "Several unique constraints are defined on the same columns",
                        entity=table_def.entity,
                    )
                table_def.constraints[constraint.name] = constraint

    def _init_primary_key(self) -> None:
        for table_def in self._table_defs.values():
            _meta = meta.get(table_def.entity, EntityPropsMeta)
            key_name = _meta.primary_key[0]
            col_defs: list[TableColumn] = []
            for att_name in _meta.primary_key[1]:
                if att_name not in table_def.columns:
                    raise EntityError(
                        f"'{att_name}' in primary key does not refer to an entity column",
                        entity=table_def.entity,
                    )
                col_defs.append(table_def.columns[att_name])
            for col_name, col_prop in _meta.columns.items():
                if col_prop.primary[1]:
                    if len(col_defs):
                        raise EntityError(
                            "Several columns have been marked as primary",
                            entity=table_def.entity,
                        )
                    key_name = col_prop.primary[0]
                    col_defs = [table_def.columns[col_name]]
            if not len(col_defs):
                raise EntityError("No primary key defined", entity=table_def.entity)
            if key_name is None:
                key_name = f"{table_def.name}_pk"
            constraint = PrimaryKeyConstraint(key_name, col_defs)
            if table_def.check_unique(constraint.columns):
                raise EntityError(
                    "Primary key is defined on the same columns as a unique constraint",
                    entity=table_def.entity,
                )
            table_def.constraints[constraint.name] = constraint

    def _init_many_to_ones(self) -> None:
        class ManyToOneTempDef:
            def __init__(
                self,
                name: str | None,
                src_cols: list[TableColumn],
                reference: str | None,
                target: type[Entity] | None,
                target_cols: list[str] | None,
                lazy: bool | Literal["subquery"],
                backref: tuple[str, bool | Literal["subquery"]] | None,
            ) -> None:
                self.name = name
                self.src_cols = src_cols
                self.reference = reference
                self.target = target
                self.target_cols = target_cols
                self.lazy = lazy
                self.backref = backref

        for table_def in self._table_defs.values():
            _meta = meta.get(table_def.entity, EntityPropsMeta)
            temp_defs: list[ManyToOneTempDef] = []
            for col_name, col_def in _meta.columns.items():
                if (_f_key := col_def.foreign_key) is not None:
                    temp_defs.append(
                        ManyToOneTempDef(
                            None,
                            [table_def.columns[col_name]],
                            _f_key.reference,
                            _f_key.target,
                            _f_key.target_cols,
                            _f_key.lazy,  # type: ignore
                            _f_key.backref,
                        )
                    )
            for tmp_def in _meta.many_to_ones:
                for att_name in tmp_def.src_cols:
                    if att_name not in table_def.columns:
                        raise EntityError(
                            f"'{att_name}' in foreign key does not match with an entity column",
                            entity=table_def.entity,
                        )
                temp_defs.append(
                    ManyToOneTempDef(
                        None,
                        list(map(lambda c: table_def.columns[c], tmp_def.src_cols)),
                        tmp_def.reference,
                        tmp_def.target,
                        tmp_def.target_cols,
                        tmp_def.lazy,  # type: ignore
                        tmp_def.backref,
                    )
                )
            for tmp_def in temp_defs:
                ref_col = tmp_def.reference
                if ref_col is not None:
                    if ref_col not in table_def.references:
                        raise EntityError(
                            f"'{ref_col}' in foreign key does not match with any reference in the entity",
                            entity=table_def.entity,
                        )
                    ref_def = table_def.references[ref_col]
                    if not isinstance(ref_def, TableReference):
                        raise EntityError(
                            f"Many-to-one reference '{ref_col}' must not be a list",
                            entity=table_def.entity,
                        )
                    target_table = ref_def.target
                else:
                    ref_def = None
                    target_table = None
                target_ent = tmp_def.target
                if target_table is None and target_ent is not None:
                    if target_ent not in self._table_defs:
                        raise EntityError(
                            f"Type {target_ent} provided in foreign key is not a registered entity",
                            entity=table_def.entity,
                        )
                    target_table = self._table_defs[target_ent]
                assert target_table is not None
                key_name = tmp_def.name
                if key_name is None:
                    key_name = f"{table_def.name}_{target_table.name}_fk"
                target_col_defs: list[TableColumn]
                if not tmp_def.target_cols:
                    primary_key = target_table.get_constraints(PrimaryKeyConstraint)[0][
                        1
                    ]
                    target_col_defs = [*primary_key.columns]
                else:
                    target_col_defs = []
                    for col in tmp_def.target_cols:
                        if col not in target_table.columns:
                            raise EntityError(
                                f"'{col}' is not a column in entity {target_table.entity}",
                                entity=table_def.entity,
                            )
                        target_col_defs.append(target_table.columns[col])
                    if not target_table.check_unique(target_col_defs):
                        raise EntityError(
                            f"({','.join(tmp_def.target_cols)}) target in foreign key is not a unique constraint on entity {target_table.entity}",
                            entity=table_def.entity,
                        )
                if len(tmp_def.src_cols) != len(target_col_defs) or list(
                    map(lambda x: x.py_type, tmp_def.src_cols)
                ) != list(map(lambda x: x.py_type, target_col_defs)):
                    raise EntityError(
                        f"({','.join(map(lambda c: c.name, tmp_def.src_cols))}) foreign key "
                        f"and {target_table.entity}({','.join(map(lambda c: c.name, target_col_defs))}) do not match",
                        entity=table_def.entity,
                    )
                foreign_def = ManyToOneConstraint(
                    key_name, tmp_def.src_cols, ref_def, target_table, target_col_defs
                )
                if ref_def is not None:
                    ref_def.constraint = foreign_def
                    ref_def.lazy = tmp_def.lazy  # type: ignore
                    if tmp_def.backref is not None:
                        back_name, back_lazy = tmp_def.backref
                        if back_name not in target_table.references:
                            raise EntityError(
                                f"'{back_name}' in backref does not match with any reference in the target entity {target_table.entity}",
                                entity=table_def.entity,
                            )
                        back_ref = target_table.references[back_name]
                        if not isinstance(back_ref, CollectionReference):
                            raise EntityError(
                                f"Many-to-one backref '{ref_col}' in {table_def.entity} must be a list",
                                entity=table_def.entity,
                            )
                        if back_ref.constraint is not None:
                            raise EntityError(
                                f"Backref '{ref_col}' in {table_def.entity} is already used by another relationship",
                                entity=table_def.entity,
                            )
                        back_ref.constraint = foreign_def
                        back_ref.lazy = back_lazy
                        ref_def.other_side = back_ref
                        back_ref.other_side = ref_def
                table_def.constraints[key_name] = foreign_def

    def _init_many_to_manies(self):
        class ManyToManyTempDef:
            def __init__(
                self,
                name: str | None,
                reference: str,
                source_cols: list[str] | None,
                target_cols: list[str] | None,
                join_table: str | None,
            ) -> None:
                self.name = name
                self.reference = reference
                self.source_cols = source_cols
                self.target_cols = target_cols
                self.join_table = join_table

        for table_def in self._table_defs.values():
            _meta = meta.get(table_def.entity, EntityPropsMeta)
            temp_defs: list[ManyToManyTempDef] = []
            for tmp_def in _meta.many_to_manies:
                temp_defs.append(
                    ManyToManyTempDef(
                        tmp_def.name,
                        tmp_def.reference,
                        tmp_def.source_cols,
                        tmp_def.target_cols,
                        tmp_def.join_table,
                    )
                )
            for tmp_def in temp_defs:
                ref_col = tmp_def.reference
                if ref_col not in table_def.references:
                    raise EntityError(
                        f"'{ref_col}' in foreign key does not match with any reference in the entity",
                        entity=table_def.entity,
                    )
                ref_def = table_def.references[ref_col]
                if not isinstance(ref_def, CollectionReference):
                    raise EntityError(
                        f"Many-to-many reference '{ref_col}' must be a list of entities",
                        entity=table_def.entity,
                    )
                target_table_def = ref_def.element
                source_columns: list[TableColumn]
                if tmp_def.source_cols is not None:
                    source_columns = []
                    for col_name in tmp_def.source_cols:
                        if col_name not in table_def.columns:
                            raise EntityError(
                                f"'{col_name}' in foreign key does not match with an entity column",
                                entity=table_def.entity,
                            )
                        source_columns.append(table_def.columns[col_name])
                else:
                    primary_key = table_def.get_constraints(PrimaryKeyConstraint)[0][1]
                    source_columns = [*primary_key.columns]
                target_columns: list[TableColumn]
                if tmp_def.target_cols is not None:
                    target_columns = []
                    for col_name in tmp_def.target_cols:
                        if col_name not in target_table_def.columns:
                            raise EntityError(
                                f"'{col_name}' in foreign key does not match with an column in target entity {target_table_def.entity}",
                                entity=table_def.entity,
                            )
                        target_columns.append(table_def.columns[col_name])
                else:
                    primary_key = table_def.get_constraints(PrimaryKeyConstraint)[0][1]
                    target_columns = [*primary_key.columns]
                join_table_name = tmp_def.join_table
                if join_table_name is None:
                    join_table_name = f"{table_def.name}_{target_table_def.name}"
                c_name = tmp_def.name
                if c_name is None:
                    c_name = f"{table_def.name}_{target_table_def.name}_fk"
                foreign_def = ManyToManyConstraint(
                    c_name,
                    ref_def,
                    source_columns,
                    join_table_name,
                    target_table_def,
                    target_columns,
                )
                if ref_def.constraint is not None:
                    raise EntityError(
                        f"Reference '{ref_col}' is already used by another relationship",
                        entity=table_def.entity,
                    )
                ref_def.constraint = foreign_def
                table_def.constraints[c_name] = foreign_def


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
        self.constraint: ManyToOneConstraint | None = None
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
        self.constraint: ManyToManyConstraint | ManyToOneConstraint | None = None
        self.other_side: CollectionReference | TableReference | None = None


class PrimaryKeyConstraint:
    def __init__(self, name: str, columns: list[TableColumn]) -> None:
        self.name = name
        self.columns = columns


class ManyToOneConstraint:
    def __init__(
        self,
        name: str,
        source_columns: list[TableColumn],
        reference: TableReference | None,
        target: "TableDefinition",
        target_columns: list[TableColumn],
    ) -> None:
        self.name = name
        self.source_columns = source_columns
        self.reference = reference
        self.target = target
        self.target_columns = target_columns


class ManyToManyConstraint:
    def __init__(
        self,
        name: str,
        reference: CollectionReference,
        source_columns: list[TableColumn],
        join_table: str,
        target: "TableDefinition",
        target_columns: list[TableColumn],
    ) -> None:
        self.name = name
        self.reference = reference
        self.source_columns = source_columns
        self.join_table = join_table
        self.target = target
        self.target_columns = target_columns


class UniqueConstraint:
    def __init__(self, name: str, columns: list[TableColumn]) -> None:
        self.name = name
        self.columns = columns


EntityT = TypeVar("EntityT", bound=Entity)
ConstraintType = (
    UniqueConstraint | PrimaryKeyConstraint | ManyToOneConstraint | ManyToManyConstraint
)
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

    def check_unique(self, columns: list[TableColumn]) -> bool:
        for constraint in {a for _, a in self.get_constraints(UniqueConstraint)}:
            for col_def in constraint.columns:
                if col_def not in columns:
                    break
            else:
                return True
        return False
