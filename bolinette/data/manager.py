from types import NoneType, UnionType
from typing import Generic, TypeVar, get_args, get_origin, get_type_hints

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
        self._init_foreign_keys()

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
                nullable = False
                origin: type | None
                if (origin := get_origin(h_type)) is not None:
                    if origin is UnionType:
                        h_args = get_args(h_type)
                        nullable = NoneType in h_args
                        h_args = tuple(a for a in h_args if a is not NoneType)
                        if len(h_args) > 1:
                            raise EntityError(
                                "Union types are not allowed",
                                entity=table_def.entity,
                                attribute=h_name,
                            )
                        h_type = h_args[0]
                if types.is_supported(h_type):
                    col_def = TableColumn(
                        h_name, h_type, types.get_sql_type(h_type), nullable
                    )
                    table_def.columns[h_name] = col_def
                    all_col_defs[h_name] = col_def
                elif h_type in self._table_defs:
                    ref_def = TableReference(h_name, self._table_defs[h_type])
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

    def _init_foreign_keys(self) -> None:
        class ForeignKeyTempDef:
            def __init__(
                self,
                name: str | None,
                src_cols: list[TableColumn],
                reference: str | None,
                target: type[Entity] | None,
                target_cols: list[str] | None,
            ) -> None:
                self.name = name
                self.src_cols = src_cols
                self.reference = reference
                self.target = target
                self.target_cols = target_cols

        for table_def in self._table_defs.values():
            _meta = meta.get(table_def.entity, EntityPropsMeta)
            temp_defs: list[ForeignKeyTempDef] = []
            for col_name, col_def in _meta.columns.items():
                if (_f_key := col_def.foreign_key) is not None:
                    temp_defs.append(
                        ForeignKeyTempDef(
                            None,
                            [table_def.columns[col_name]],
                            _f_key.reference,
                            _f_key.target,
                            _f_key.target_cols,
                        )
                    )
            for tmp_def in _meta.foreign_keys:
                for att_name in tmp_def.src_cols:
                    if att_name not in table_def.columns:
                        raise EntityError(
                            f"'{att_name}' in foreign key does not match with an entity column",
                            entity=table_def.entity,
                        )
                temp_defs.append(
                    ForeignKeyTempDef(
                        None,
                        list(map(lambda c: table_def.columns[c], tmp_def.src_cols)),
                        tmp_def.reference,
                        tmp_def.target,
                        tmp_def.target_cols,
                    )
                )
            for tmp_def in temp_defs:
                ref_col = tmp_def.reference
                if ref_col is not None:
                    if ref_col not in table_def.references:
                        raise EntityError(
                            f"'{ref_col}' in foreign_key does not match with any reference in the entity",
                            entity=table_def.entity,
                        )
                    ref_def = table_def.references[ref_col]
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
                target_col_defs: list[TableColumn] = []
                if not tmp_def.target_cols:
                    primary_key = target_table.get_constraints(PrimaryKeyConstraint)[0][
                        1
                    ]
                    target_col_defs = [*primary_key.columns]
                else:
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
                foreign_def = ForeignKeyConstraint(
                    key_name, tmp_def.src_cols, ref_def, target_table, target_col_defs
                )
                if ref_def is not None:
                    ref_def.foreign_key = foreign_def
                table_def.constraints[key_name] = foreign_def


class TableColumn:
    def __init__(self, name: str, py_type: type, sql_type, nullable: bool) -> None:
        self.name = name
        self.py_type = py_type
        self.sql_type = sql_type
        self.nullable = nullable


class TableReference:
    def __init__(self, name: str, target: "TableDefinition") -> None:
        self.name = name
        self.target = target
        self.foreign_key: ForeignKeyConstraint | None = None


class PrimaryKeyConstraint:
    def __init__(self, name: str, columns: list[TableColumn]) -> None:
        self.name = name
        self.columns = columns


class ForeignKeyConstraint:
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
        self.references: dict[str, TableReference] = {}
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
