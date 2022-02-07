import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette.core import BolinetteContext, InstantiableAttribute
from bolinette.data import ext, DataContext, Model, Repository, SimpleService
from bolinette.data.models import Column, Relationship, Reference, ColumnList
from bolinette.data.database.engines import RelationalDatabase
from bolinette.exceptions import InitError, InternalError


@ext.init_func()
async def init_model_classes(context: BolinetteContext):
    def _init_model(model: Model):
        def _init_column(_name: str, _attr: InstantiableAttribute[Column]):
            return _attr.instantiate(name=_name, model=model)

        def _init_relationship(_name: str, _attr: InstantiableAttribute[Relationship]):
            _target_name = _attr.pop("model_name")
            _target_model = context.inject.require(
                "model", _target_name, immediate=True
            )
            _fk_name = _attr.pop("foreign_key")
            _foreign_key = None
            if _fk_name is not None:
                _foreign_key = getattr(model, _fk_name, None)
            _remote_name = _attr.pop("remote_side")
            _remote_side = None
            _secondary_name = _attr.pop("secondary")
            _secondary = None
            if _secondary_name is not None:
                _secondary = context.inject.require(
                    "model", _secondary_name, immediate=True
                )
            if _remote_name is not None:
                _remote_side = getattr(model, _remote_name)
            return _attr.instantiate(
                name=_name,
                model=model,
                target_model=_target_model,
                secondary=_secondary,
                foreign_key=_foreign_key,
                remote_side=_remote_side,
            )

        def _init_reference(_col: Column, _attr: InstantiableAttribute[Reference]):
            _target_name = _attr.pop("model_name")
            _target_model = context.inject.require(
                "model", _target_name, immediate=True
            )
            _target_col_name = _attr.pop("column_name")
            _target_column = getattr(_target_model, _target_col_name, None)
            if _target_column is None:
                raise InitError(
                    f"{model.__blnt__.name}.{_col.name}: "
                    f'no "{_target_col_name}" column in "{_target_name}" model'
                )
            return _attr.instantiate(
                model=model,
                column=_col,
                target_model=_target_model,
                target_column=_target_column,
            )

        # Instantiate mixins
        for mixin_name in model.__blnt__.mixins:
            model.__props__.mixins[mixin_name] = ext.cache.collect_by_name(
                "mixin", mixin_name
            )()

        # Instantiate columns
        for col_name, attr_col in model.__props__.get_instantiable(Column):
            setattr(model, col_name, _init_column(col_name, attr_col))
        # Add mixin columns
        for _, mixin in model.__props__.mixins.items():
            for col_name, attr_col in mixin.columns().items():
                setattr(model, col_name, _init_column(col_name, attr_col))

        # Process auto generated primary keys
        primary = [c for _, c in model.__props__.get_columns() if c.primary_key]
        if not primary:
            model.__props__.primary = None
        else:
            if len(primary) == 1 and primary[0].auto_increment is None:
                primary[0].auto_increment = True
            model.__props__.primary = primary
        for column in primary:
            column.nullable = False
        # Find entity key
        entity_key = [c for _, c in model.__props__.get_columns() if c.entity_key]
        if not entity_key:
            model.__props__.entity_key = model.__props__.primary
        else:
            model.__props__.entity_key = entity_key
        if model.__props__.entity_key is None:
            raise InitError(
                f'No entity key defined for "{model.__blnt__.name}" model. '
                "Mark one column or more as entity_key=True."
            )

        # Process relationships
        for rel_name, attr_rel in model.__props__.get_instantiable(Relationship):
            setattr(model, rel_name, _init_relationship(rel_name, attr_rel))
        # Add mixin relationships
        for _, mixin in model.__props__.mixins.items():
            for rel_name, attr_rel in mixin.relationships().items():
                setattr(model, rel_name, _init_relationship(rel_name, attr_rel))

        # Instantiate references
        for col_name, col in model.__props__.get_columns():
            if isinstance(col.reference, InstantiableAttribute):
                col.reference = _init_reference(col, col.reference)
        # Instantiate back references
        added_back_refs: dict[Model, list[ColumnList]] = {}
        for rel_name, rel in model.__props__.get_relationships():
            if isinstance(rel.backref, InstantiableAttribute):
                rel.backref = rel.backref.instantiate(model=model, relationship=rel)
                if rel.backref.key not in added_back_refs:
                    added_back_refs[rel.target_model] = []
                added_back_refs[rel.target_model].append(
                    ColumnList(rel.backref.key, rel.target_model, model)
                )

    for model_cls in ext.cache.collect_by_type(Model):
        context.inject.register(
            model_cls, "model", model_cls.__blnt__.name, func=_init_model
        )


@ext.init_func()
async def init_relational_models(context: BolinetteContext):
    models = {}
    for model_cls in context.inject.registered(of_type=Model):
        model: Model = context.inject.require(model_cls, immediate=True)
        if model.__props__.database.relational:
            models[model.__blnt__.name] = model
    orm_tables = {}
    orm_cols: dict[str, dict[str, sqlalchemy.Column]] = {}
    for model_name, model in models.items():
        orm_cols[model_name] = {}
        for col_name, col in model.__props__.get_columns():
            ref = None
            if col.reference:
                ref = sqlalchemy.ForeignKey(col.reference.target_path)
            orm_cols[model_name][col_name] = sqlalchemy.Column(
                col_name,
                col.type.sqlalchemy_type,
                ref,
                default=col.default,
                index=col.entity_key,
                primary_key=col.primary_key,
                nullable=col.nullable,
                unique=col.unique,
                autoincrement=col.auto_increment,
            )
        if not isinstance(model.__props__.database, RelationalDatabase):
            raise InternalError(f"model.not_relational:{model.__blnt__.name}")
        orm_tables[model_name] = sqlalchemy.Table(
            model_name,
            model.__props__.database.base.metadata,
            *(orm_cols[model_name].values()),
        )

    for model_name, model in models.items():
        orm_defs = {}
        for rel_name, rel in model.__props__.get_relationships():
            kwargs = {}
            rel.name = rel_name
            if rel.backref:
                kwargs["backref"] = sqlalchemy_orm.backref(
                    rel.backref.key, lazy=rel.backref.lazy
                )
            if rel.foreign_key:
                kwargs["foreign_keys"] = orm_cols[model_name][rel.foreign_key.name]
            if rel.remote_side:
                kwargs["remote_side"] = orm_cols[model_name][rel.remote_side.name]
            if rel.secondary:
                kwargs["secondary"] = orm_tables[rel.secondary.__blnt__.name]
            orm_defs[rel_name] = sqlalchemy_orm.relationship(
                rel.target_model_name, lazy=rel.lazy, **kwargs
            )

        orm_defs["__table__"] = orm_tables[model_name]
        if not isinstance(model.__props__.database, RelationalDatabase):
            raise InternalError(f"model.not_relational:{model.__blnt__.name}")
        orm_model = type(model_name, (model.__props__.database.base,), orm_defs)

        for att_name, attribute in model.__props__.get_properties():
            setattr(orm_model, att_name, property(attribute.function))

        if isinstance(model.__props__.database, RelationalDatabase):
            model.__props__.database.add_table(model_name, orm_model)


@ext.init_func()
async def init_databases(_, data_ctx: DataContext):
    await data_ctx.db.create_all()


@ext.init_func()
async def init_repositories(context: BolinetteContext):
    for model_cls in context.inject.registered(of_type=Model):
        model: Model = context.inject.require(model_cls, immediate=True)
        model.__props__.repo = context.inject.instantiate_type(
            Repository, args={Model: model}
        )


@ext.init_func()
async def init_mappings(context: BolinetteContext, data_ctx: DataContext):
    for model_cls in context.inject.registered(of_type=Model):
        model: Model = context.inject.require(model_cls, immediate=True)
        data_ctx.mapper.register(model)


@ext.init_func()
async def init_services(context: BolinetteContext):
    for service_cls in ext.cache.collect_by_type(SimpleService):
        context.inject.register(service_cls, "service", service_cls.__blnt__.name)
