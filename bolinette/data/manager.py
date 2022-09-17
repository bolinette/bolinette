from types import NoneType, UnionType
from typing import Generic, TypeVar, get_args, get_origin, get_type_hints

from bolinette.core import Cache, Logger, init_method, injectable, meta
from bolinette.core.utils import AttributeUtils
from bolinette.data import DataSection, __data_cache__
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
        self._entities: dict[type, _EntityDef] = {}

    @init_method
    def init(self) -> None:
        self._init_models()
        self._init_columns()
        self._init_unique_constraints()
        self._init_primary_key()

    def _init_models(self) -> None:
        _type = type[Entity]
        for cls in self._cache[EntityMeta, _type]:
            entity_meta = meta.get(cls, EntityMeta)
            entity_def = _EntityDef(entity_meta.table_name, cls)
            self._entities[cls] = entity_def

    def _init_columns(self) -> None:
        for entity_def in self._entities.values():
            hints: dict[str, type] = get_type_hints(entity_def.cls)
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
                                entity=entity_def.cls,
                                attribute=h_name,
                            )
                entity_def.attributes[h_name] = EntityAttribute(
                    h_name, h_type, nullable
                )

    def _init_unique_constraints(self) -> None:
        for entity_def in self._entities.values():
            _meta = meta.get(entity_def.cls, EntityPropsMeta)
            all_entity_columns = dict(entity_def.get_attributes(EntityAttribute))
            key_defs: list[tuple[str | None, list[str]]] = []
            for c_name, key in _meta.unique_constraints:
                key_defs.append((c_name, key))
            for col_name, col_def in _meta.columns.items():
                if col_def.unique[1]:
                    key_defs.append((col_def.unique[0], [col_name]))
            for c_name, key in key_defs:
                key_columns: list[EntityAttribute] = []
                for att_name in key:
                    if att_name not in all_entity_columns:
                        raise EntityError(
                            f"'{att_name}' in unique constraint does not refer to an entity column",
                            entity=entity_def.cls,
                        )
                    key_columns.append(all_entity_columns[att_name])
                if c_name is None:
                    c_name = f"{entity_def.name}_{'_'.join(key)}_u"
                constraint = UniqueConstraint(c_name, key_columns)
                if entity_def.check_unique(constraint.columns):
                    raise EntityError(
                        "Several unique constraints are defined on the same columns",
                        entity=entity_def.cls,
                    )
                entity_def.constraints[constraint.name] = constraint

    def _init_primary_key(self) -> None:
        for entity_def in self._entities.values():
            _meta = meta.get(entity_def.cls, EntityPropsMeta)
            all_entity_columns = dict(entity_def.get_attributes(EntityAttribute))
            key_columns: list[EntityAttribute] = []
            c_name, att_names = _meta.primary_key
            if not len(att_names):
                raise EntityError("No primary key defined", entity=entity_def.cls)
            for att_name in att_names:
                if att_name not in all_entity_columns:
                    raise EntityError(
                        f"'{att_name}' in primary key does not refer to an entity column",
                        entity=entity_def.cls,
                    )
                key_columns.append(all_entity_columns[att_name])
            if c_name is None:
                c_name = f"{entity_def.name}_pk"
            constraint = PrimaryKeyConstraint(c_name, key_columns)
            if entity_def.check_unique(constraint.columns):
                raise EntityError(
                    "Primary key is defined on the same columns as a unique constraint",
                    entity=entity_def.cls,
                )
            entity_def.constraints[constraint.name] = constraint

    def _init_foreign_keys(self) -> None:
        for entity_def in self._entities.values():
            _meta = meta.get(entity_def.cls, EntityPropsMeta)
            temp_defs = [*_meta.foreign_keys]
            for col_name, col_def in _meta.columns.items():
                if (_f_key := col_def.foreign_key) is not None:
                    temp_defs.append(
                        EntityPropsMeta.ForeignKeyTempDef(
                            None,
                            [col_name],
                            _f_key.reference,
                            _f_key.target,
                            _f_key.target_cols,
                        )
                    )


class EntityAttribute:
    def __init__(self, name: str, py_type: type, nullable: bool) -> None:
        self.name = name
        self.py_type = py_type
        self.nullable = nullable


class PrimaryKeyConstraint:
    def __init__(self, name: str, columns: list[EntityAttribute]) -> None:
        self.name = name
        self.columns = columns


class ForeignKeyConstraint:
    def __init__(self, name: str) -> None:
        self.name = name


class UniqueConstraint:
    def __init__(self, name: str, columns: list[EntityAttribute]) -> None:
        self.name = name
        self.columns = columns


EntityT = TypeVar("EntityT", bound=Entity)
AttributeType = EntityAttribute
AttributeT = TypeVar("AttributeT", bound=AttributeType)
ConstraintType = UniqueConstraint | PrimaryKeyConstraint
ConstraintT = TypeVar("ConstraintT", bound=ConstraintType)


class _EntityDef(Generic[EntityT]):
    def __init__(self, name: str, cls: type[EntityT]) -> None:
        self.name = name
        self.cls = cls
        self.attributes: dict[str, AttributeType] = {}
        self.constraints: dict[str, ConstraintType] = {}

    def get_attributes(
        self,
        of_type: type[AttributeT],
    ) -> list[tuple[str, AttributeT]]:
        return [(n, a) for n, a in self.attributes.items() if isinstance(a, of_type)]

    def get_constraints(
        self,
        of_type: type[ConstraintT],
    ) -> list[tuple[str, ConstraintT]]:
        return [(n, a) for n, a in self.constraints.items() if isinstance(a, of_type)]

    def check_unique(self, columns: list[EntityAttribute]) -> bool:
        for constraint in {a for _, a in self.get_constraints(UniqueConstraint)}:
            for col_def in constraint.columns:
                if col_def not in columns:
                    break
            else:
                return True
        return False
