from types import NoneType, UnionType
from typing import Any, Generic, TypeVar, get_args, get_origin, get_type_hints

from bolinette.core import Cache, Logger, init_method, injectable, meta
from bolinette.core.utils import AttributeUtils
from bolinette.data import DataSection, __data_cache__
from bolinette.data.entity import Entity, EntityMeta, EntityPropsMeta
from bolinette.data.exceptions import EntityError, ModelError
from bolinette.data.model import (
    Column,
    ForeignKey,
    ManyToOne,
    Model,
    ModelMeta,
    PrimaryKey,
)


@injectable(cache=__data_cache__)
class DatabaseManager:
    def __init__(self, section: DataSection, models: "ModelManager") -> None:
        self._section = section
        self._models = models


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


@injectable(cache=__data_cache__)
class ModelManager:
    def __init__(
        self, cache: Cache, attrs: AttributeUtils, logger: "Logger[ModelManager]"
    ) -> None:
        self._cache = cache
        self._models: dict[type, _ModelDef] = {}
        self._attrs = attrs
        self._logger = logger

    @init_method
    def init(self) -> None:
        self._init_models()
        self._init_columns()
        self._init_unique_constraints()
        self._init_primary_key()
        self._init_references()
        self._init_many_to_ones()
        self._validate_entities()

    def _init_models(self) -> None:
        _type = type[Model]
        for cls in self._cache[ModelMeta, _type]:
            model_meta = meta.get(cls, ModelMeta)
            entity = model_meta.entity
            if entity in self._models:
                model_def = self._models[entity]
                raise ModelError(
                    f"Entity {entity} is already used by model {model_def.model}",
                    model=cls,
                )
            model_def = _ModelDef(model_meta.table_name, cls, entity)
            self._models[entity] = model_def

    def _init_columns(self) -> None:
        for model_def in self._models.values():
            for col_name, col in self._attrs.get_cls_attrs(
                model_def.model, of_type=Column
            ):
                col_def = _ColumnDef(
                    col,
                    col_name,
                    model_def,
                    col.primary_key,
                    col.entity_key,
                    col.unique,
                )
                model_def.attributes[col_name] = col_def

    def _init_unique_constraints(self) -> None:
        for model_def in self._models.values():
            constraints: list[_UniqueDef] = []
            for col_name, col in (
                (n, c) for n, c in model_def.attrs(_ColumnDef) if c.unique
            ):
                constraints.append(_UniqueDef(f"{model_def.name}_{col_name}_u", [col]))
            custom_constraints = [
                (name, attr)
                for name, attr in self._attrs.get_cls_attrs(
                    model_def.model, of_type=UniqueConstraint
                )
            ]
            all_col_defs = [c for _, c in model_def.attrs(_ColumnDef)]
            for const_name, constraint in custom_constraints:
                const_col_defs: list[_ColumnDef] = []
                for col in constraint.columns:
                    const_col_defs.append(
                        next(c for c in all_col_defs if c.column is col)
                    )
                constraints.append(_UniqueDef(const_name, const_col_defs))
            for constraint in constraints:
                if model_def.check_unique(constraint.columns):
                    raise ModelError(
                        "Another unique constraint has already been defined with the same columns",
                        model=model_def.model,
                        attribute=constraint.name,
                    )
                model_def.attributes[constraint.name] = constraint

    def _init_primary_key(self) -> None:
        for model_def in self._models.values():
            keys: list[_PrimaryKeyDef] = []
            defined_key = [
                c
                for c in model_def.attributes.values()
                if isinstance(c, _ColumnDef) and c.primary_key
            ]
            if len(defined_key):
                keys.append(_PrimaryKeyDef(f"{model_def.name}_pk", defined_key))
            custom_keys = [
                (name, attr)
                for name, attr in self._attrs.get_cls_attrs(
                    model_def.model, of_type=PrimaryKey
                )
            ]
            all_col_defs = [c for _, c in model_def.attrs(_ColumnDef)]
            for key_name, custom_key in custom_keys:
                key_col_defs: list[_ColumnDef] = []
                for col in custom_key.columns:
                    key_col_defs.append(
                        next(c for c in all_col_defs if c.column is col)
                    )
                keys.append(_PrimaryKeyDef(key_name, key_col_defs))
            if not len(keys):
                raise ModelError("No primary key defined", model=model_def.model)
            if len(keys) > 1:
                raise ModelError(
                    "Several primary keys cannot be defined", model=model_def.model
                )
            key = keys[0]
            if model_def.check_unique(key.columns):
                raise ModelError(
                    "A unique constraint has already been defined with the same columns as the primary key",
                    model=model_def.model,
                )
            model_def.attributes[key.name] = key

    def _init_references(self) -> None:
        for model_def in self._models.values():
            defined_keys: list[
                tuple[str | None, str, type[Any], list[Column], list[str] | None]
            ] = []
            for col_name, col_def in model_def.attrs(_ColumnDef):
                if (ref := col_def.column.reference) is not None:
                    defined_keys.append(
                        (
                            None,
                            col_name,
                            ref.entity,
                            [col_def.column],
                            list(ref.columns) if ref.columns else None,
                        )
                    )
            for key_name, key in self._attrs.get_cls_attrs(
                model_def.model, of_type=ForeignKey
            ):
                defined_keys.append(
                    (
                        key_name,
                        key_name,
                        key.entity,
                        list(key.source_cols),
                        list(key.target_cols) if key.target_cols else None,
                    )
                )
            for key_name, attr_name, entity, source_cols, target_cols in defined_keys:
                if entity not in self._models:
                    raise ModelError(
                        f"{entity} is not known entity",
                        model=model_def.model,
                        attribute=attr_name,
                    )
                all_source_col_defs = [c for _, c in model_def.attrs(_ColumnDef)]
                source_col_defs: list[_ColumnDef] = []
                for col in source_cols:
                    source_col_defs.append(
                        next(c for c in all_source_col_defs if c.column is col)
                    )
                target_model_def = self._models[entity]
                target_col_defs: list[_ColumnDef] = []
                if target_cols is None:
                    primary_key_def = model_def.attrs(_PrimaryKeyDef)[0][1]
                    target_col_defs = list(primary_key_def.columns)
                else:
                    for column in target_cols:
                        if column not in target_model_def.attributes:
                            raise ModelError(
                                f"Target column '{column}' does not exist on {target_model_def.model}",
                                model=model_def.model,
                                attribute=attr_name,
                            )
                        target_col_def = target_model_def.attributes[column]
                        if isinstance(target_col_def, _ColumnDef):
                            target_col_defs.append(target_col_def)
                if not key_name:
                    key_name = f"{model_def.name}_{target_model_def.name}_fk"
                if len(source_col_defs) != len(target_col_defs):
                    raise ModelError(
                        f"Composite key has different length on the two sides",
                        model=model_def.model,
                        attribute=attr_name,
                    )
                model_def.attributes[key_name] = _ForeignDef(
                    key_name,
                    attr_name,
                    model_def,
                    source_col_defs,
                    target_model_def,
                    target_col_defs,
                )

    def _init_many_to_ones(self) -> None:
        for model_def in self._models.values():
            for rel_name, rel in self._attrs.get_cls_attrs(
                model_def.model, of_type=ManyToOne
            ):
                if rel.foreign_key.reference is None:
                    raise ModelError(
                        "Given foreign key does not reference any column",
                        model=model_def.model,
                        attribute=rel_name,
                    )
                target = rel.foreign_key.reference.entity
                target_model_def = self._models[target]
                mto_def = _ManyToOneDef(rel_name, model_def, target_model_def)
                model_def.attributes[rel_name] = mto_def
                if rel.backref is not None:
                    otm_def = _OneToManyDef(
                        rel.backref.key, target_model_def, model_def
                    )
                    target_model_def.attributes[rel.backref.key] = otm_def

    def _validate_entities(self) -> None:
        for model_def in self._models.values():
            entity = model_def.entity
            hints: dict[str, type] = get_type_hints(entity)
            for att_name, attr in model_def.attributes.items():
                if type(attr) not in {_ColumnDef, _OneToManyDef, _ManyToOneDef}:
                    continue
                if att_name not in hints:
                    raise ModelError(
                        f"No '{att_name}' annotated attribute found in {entity}",
                        model=model_def.model,
                    )
                h_type = hints[att_name]
                h_arg = None
                if get_origin(h_type) is list:
                    h_arg = get_args(h_type)[0]
                    h_type = list
                p_type = None
                p_arg = None
                if isinstance(attr, _ColumnDef):
                    p_type = attr.column.type.python_type
                elif isinstance(attr, _ManyToOneDef):
                    p_type = attr.target.entity
                elif isinstance(attr, _OneToManyDef):
                    p_type = list
                    p_arg = attr.target.entity
                if p_type is not None and p_type is not h_type:
                    raise ModelError(
                        f"Type {h_type} is not assignable to column type {p_type}",
                        entity=model_def.entity,
                        attribute=att_name,
                    )
                if p_arg is not None and p_arg is not h_arg:
                    if h_arg is None:
                        raise ModelError(
                            f"Type {list} needs a generic argument",
                            entity=model_def.entity,
                            attribute=att_name,
                        )
                    raise ModelError(
                        f"Type list[{h_arg}] is not assignable to column type list[{p_arg}]",
                        entity=model_def.entity,
                        attribute=att_name,
                    )


class EntityAttribute:
    def __init__(self, name: str, py_type: type, nullable: bool) -> None:
        self.name = name
        self.py_type = py_type
        self.nullable = nullable


class _ColumnDef:
    def __init__(
        self,
        column: Column,
        name: str,
        model: "_ModelDef",
        primary_key: bool,
        entity_key: bool,
        unique: bool,
    ) -> None:
        self.column = column
        self.name = name
        self.model = model
        self.primary_key = primary_key
        self.entity_key = entity_key
        self.unique = unique


class _PrimaryKeyDef:
    def __init__(self, name: str, columns: list[_ColumnDef]) -> None:
        self.name = name
        self.columns = columns


class PrimaryKeyConstraint:
    def __init__(self, name: str, columns: list[EntityAttribute]) -> None:
        self.name = name
        self.columns = columns


class _UniqueDef:
    def __init__(self, name: str, columns: list[_ColumnDef]) -> None:
        self.name = name
        self.columns = columns


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


T = TypeVar("T")


class _ModelDef:
    def __init__(self, name: str, model: type[Model], entity: type[Any]) -> None:
        self.name = name
        self.model = model
        self.entity = entity
        self.attributes: dict[
            str,
            _ColumnDef
            | _ManyToOneDef
            | _OneToManyDef
            | _PrimaryKeyDef
            | _UniqueDef
            | _ForeignDef,
        ] = {}

    def attrs(
        self,
        of_type: type[T],
    ) -> list[tuple[str, T]]:
        return [(n, a) for n, a in self.attributes.items() if isinstance(a, of_type)]

    def check_unique(self, columns: list[_ColumnDef]) -> bool:
        for constraint in {a for _, a in self.attrs(_UniqueDef)}:
            for col_def in constraint.columns:
                if col_def not in columns:
                    break
            else:
                return True
        return False


class _ForeignDef:
    def __init__(
        self,
        name: str,
        attr_name: str,
        source: _ModelDef,
        source_cols: list[_ColumnDef],
        target: _ModelDef,
        target_cols: list[_ColumnDef],
    ) -> None:
        self.name = name
        self.attr_name = attr_name
        self.source = source
        self.source_cols = source_cols
        self.target = target
        self.target_cols = target_cols


class _ManyToOneDef:
    def __init__(self, name: str, origin: _ModelDef, target: _ModelDef) -> None:
        self.name = name
        self.origin = origin
        self.target = target


class _OneToManyDef:
    def __init__(self, name: str, origin: _ModelDef, target: _ModelDef) -> None:
        self.name = name
        self.origin = origin
        self.target = target
