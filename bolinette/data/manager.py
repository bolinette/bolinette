from typing import Any, get_args, get_origin, get_type_hints

from bolinette.core import Cache, Logger, init_method, injectable, meta
from bolinette.core.utils import AttributeUtils
from bolinette.data import DataSection, __data_cache__
from bolinette.data.exceptions import ModelError
from bolinette.data.model import Column, ManyToOne, Model, ModelMeta


@injectable(cache=__data_cache__)
class DatabaseManager:
    def __init__(self, section: DataSection, models: "ModelManager") -> None:
        self._section = section
        self._models = models


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

    def _init_columns(self):
        for model_def in self._models.values():
            for col_name, col in self._attrs.get_cls_attrs(
                model_def.model, of_type=Column
            ):
                col_def = _ColumnDef(
                    col, col_name, model_def, col.primary_key, col.entity_key
                )
                model_def.attributes[col_name] = col_def
            model_def.primary_key = [
                c
                for c in model_def.attributes.values()
                if isinstance(c, _ColumnDef) and c.primary_key
            ]
            if not model_def.primary_key:
                raise ModelError(f"No primary key defined", model=model_def.model)
            model_def.entity_key = [
                c
                for c in model_def.attributes.values()
                if isinstance(c, _ColumnDef) and c.entity_key
            ]
            if not model_def.entity_key:
                model_def.entity_key = list(model_def.primary_key)

    def _init_references(self):
        for model_def in self._models.values():
            for att_name, attr in model_def.attributes.items():
                if not isinstance(attr, _ColumnDef):
                    continue
                if (ref := attr.column.reference) is not None:
                    if ref.entity not in self._models:
                        raise ModelError(
                            f"{ref.entity} is not known entity",
                            model=model_def.model,
                            column=att_name,
                        )
                    target_model = self._models[ref.entity]
                    if ref.columns is None:
                        target_cols = list(target_model.primary_key)
                    else:
                        target_cols = []
                        for column in ref.columns:
                            if column not in target_model.attributes:
                                raise ModelError(
                                    f"Target column '{column}' does not exist on {target_model.model}",
                                    model=model_def.model,
                                    column=att_name,
                                )
                            target_col = target_model.attributes[column]
                            if not isinstance(target_col, _ColumnDef):
                                raise ModelError(
                                    f"Target attribute '{column}' is not a column",
                                    model=model_def.model,
                                    column=att_name,
                                )
                            if target_col.column.type is not attr.column.type:
                                raise ModelError(
                                    "Type does not match referenced column type",
                                    model=model_def.model,
                                    column=att_name,
                                )
                            target_cols.append(target_col)
                    ref_def = _ReferenceDef(target_model, target_cols)
                    attr.reference = ref_def

    def _init_many_to_ones(self):
        for model_def in self._models.values():
            for rel_name, rel in self._attrs.get_cls_attrs(
                model_def.model, of_type=ManyToOne
            ):
                if rel.foreign_key.reference is None:
                    raise ModelError(
                        "Given foreign key does not reference any column",
                        model=model_def.model,
                        rel=rel_name,
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

    def _validate_entities(self):
        for model_def in self._models.values():
            entity = model_def.entity
            hints: dict[str, type] = get_type_hints(entity)
            for att_name, attr in model_def.attributes.items():
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


class _ModelDef:
    def __init__(self, name: str, model: type[Model], entity: type[Any]) -> None:
        self.name = name
        self.model = model
        self.entity = entity
        self.attributes: dict[str, _ColumnDef | _ManyToOneDef | _OneToManyDef] = {}
        self.primary_key: list[_ColumnDef] = []
        self.entity_key: list[_ColumnDef] = []


class _ReferenceDef:
    def __init__(self, model: _ModelDef, columns: "list[_ColumnDef]") -> None:
        self.model = model
        self.columns = columns


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


class _ColumnDef:
    def __init__(
        self,
        column: Column,
        name: str,
        model: _ModelDef,
        primary_key: bool,
        entity_key: bool,
    ) -> None:
        self.column = column
        self.name = name
        self.model = model
        self.primary_key = primary_key
        self.entity_key = entity_key
        self.reference: _ReferenceDef | None = None