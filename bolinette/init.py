import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import abc, blnt, core, web, Extensions
from bolinette.decorators import init_func
from bolinette.exceptions import InitError


class TestObj(abc.WithContext):
    def __init__(self, context, value: int) -> None:
        super().__init__(context)
        self.value = value


@init_func(extension=Extensions.MODELS)
async def init_model_classes(context: blnt.BolinetteContext):
    def _init_model(model: core.Model):
        def _init_column(_name: str, _attr: blnt.InstantiableAttribute[core.models.Column]):
            return _attr.instantiate(name=_name, model=model)

        def _init_relationship(_name: str, _attr: blnt.InstantiableAttribute[core.models.Relationship]):
            _target_name = _attr.pop('model_name')
            _target_model = context.inject.require('model', _target_name, immediate=True)
            _fk_name = _attr.pop('foreign_key')
            _foreign_key = None
            if _fk_name is not None:
                _foreign_key = getattr(model, _fk_name, None)
            _remote_name = _attr.pop('remote_side')
            _remote_side = None
            _secondary_name = _attr.pop('secondary')
            _secondary = None
            if _secondary_name is not None:
                _secondary = context.inject.require('model', _secondary_name, immediate=True)
            if _remote_name is not None:
                _remote_side = getattr(model, _remote_name)
            return _attr.instantiate(name=_name, model=model, target_model=_target_model, secondary=_secondary,
                                     foreign_key=_foreign_key, remote_side=_remote_side)

        def _init_reference(_col: core.models.Column, _attr: blnt.InstantiableAttribute[core.models.Reference]):
            _target_name = _attr.pop('model_name')
            _target_model = context.inject.require('model', _target_name, immediate=True)
            _target_col_name = _attr.pop('column_name')
            _target_column = getattr(_target_model, _target_col_name, None)
            if _target_column is None:
                raise InitError(f'{model.__blnt__.name}.{_col.name}: '
                                f'no "{_target_col_name}" column in "{_target_name}" model')
            return _attr.instantiate(model=model, column=_col,
                                     target_model=_target_model, target_column=_target_column)

        # Instantiate mixins
        for mixin_name in model.__blnt__.mixins:
            if mixin_name not in blnt.cache.mixins:
                raise InitError(f'Model "{model_name}": mixin "{mixin_name}" is not defined')
            model.__props__.mixins[mixin_name] = blnt.cache.mixins[mixin_name]()

        # Instantiate columns
        for col_name, attr_col in model.__props__.get_instantiable(core.models.Column):
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
            raise InitError(f'No entity key defined for "{model.__blnt__.name}" model. '
                            'Mark one column or more as entity_key=True.')

        # Process relationships
        for rel_name, attr_rel in model.__props__.get_instantiable(core.models.Relationship):
            setattr(model, rel_name, _init_relationship(rel_name, attr_rel))
        # Add mixin relationships
        for _, mixin in model.__props__.mixins.items():
            for rel_name, attr_rel in mixin.relationships().items():
                setattr(model, rel_name, _init_relationship(rel_name, attr_rel))

        # Instantiate references
        for col_name, col in model.__props__.get_columns():
            if isinstance(col.reference, blnt.InstantiableAttribute):
                col.reference = _init_reference(col, col.reference)
        # Instantiate back references
        added_back_refs: dict[core.Model, list[core.models.ColumnList]] = {}
        for rel_name, rel in model.__props__.get_relationships():
            if isinstance(rel.backref, blnt.InstantiableAttribute):
                rel.backref = rel.backref.instantiate(model=model, relationship=rel)
                if rel.backref.key not in added_back_refs:
                    added_back_refs[rel.target_model] = []
                added_back_refs[rel.target_model].append(
                    core.models.ColumnList(rel.backref.key, rel.target_model, model))

    for model_name, model_cls in blnt.cache.models.items():
        context.inject.register(model_cls, 'model', model_name, func=_init_model)


@init_func(extension=Extensions.MODELS)
async def init_relational_models(context: blnt.BolinetteContext):
    models = {}
    for model_cls in context.inject.registered(of_type=core.Model):
        model = context.inject.require(model_cls, immediate=True)
        if model.__props__.database.relational:
            models[model.__blnt__.name] = model
    orm_tables = {}
    orm_cols: dict[str, dict[str, sqlalchemy.Column]] = {}
    for model_name, model in models.items():
        orm_cols[model_name] = {}
        for att_name, attribute in model.__props__.get_columns():
            ref = None
            if attribute.reference:
                ref = sqlalchemy.ForeignKey(attribute.reference.target_path)
            orm_cols[model_name][att_name] = sqlalchemy.Column(
                att_name, attribute.type.sqlalchemy_type, ref,
                default=attribute.default, index=attribute.entity_key,
                primary_key=attribute.primary_key, nullable=attribute.nullable,
                unique=attribute.unique, autoincrement=attribute.auto_increment)
        orm_tables[model_name] = sqlalchemy.Table(model_name,
                                                  model.__props__.database.base.metadata,
                                                  *(orm_cols[model_name].values()))

    for model_name, model in models.items():
        orm_defs = {}
        for att_name, attribute in model.__props__.get_relationships():
            kwargs = {}
            attribute.name = att_name
            if attribute.backref:
                kwargs['backref'] = sqlalchemy_orm.backref(attribute.backref.key, lazy=attribute.backref.lazy)
            if attribute.foreign_key:
                kwargs['foreign_keys'] = orm_cols[model_name][attribute.foreign_key.name]
            if attribute.remote_side:
                kwargs['remote_side'] = orm_cols[model_name][attribute.remote_side.name]
            if attribute.secondary:
                kwargs['secondary'] = orm_tables[attribute.secondary.__blnt__.name]
            orm_defs[att_name] = sqlalchemy_orm.relationship(attribute.target_model_name, lazy=attribute.lazy, **kwargs)

        orm_defs['__table__'] = orm_tables[model_name]
        orm_model = type(model_name, (model.__props__.database.base,), orm_defs)

        for att_name, attribute in model.__props__.get_properties():
            setattr(orm_model, att_name, property(attribute.function))

        model.__props__.database.add_table(model_name, orm_model)


@init_func(extension=Extensions.MODELS)
async def init_databases(context: blnt.BolinetteContext):
    await context.db.create_all()


@init_func(extension=Extensions.MODELS)
async def init_repositories(context: blnt.BolinetteContext):
    for model_cls in context.inject.registered(of_type=core.Model):
        model: core.Model = context.inject.require(model_cls, immediate=True)
        model.__props__.repo = core.Repository(context, model)


@init_func(extension=Extensions.MODELS)
async def init_mappings(context: blnt.BolinetteContext):
    for model_cls in context.inject.registered(of_type=core.Model):
        model = context.inject.require(model_cls, immediate=True)
        context.mapper.register(model)


@init_func(extension=Extensions.MODELS)
async def init_services(context: blnt.BolinetteContext):
    for service_name, service_cls in blnt.cache.services.items():
        context.inject.register(service_cls, 'service', service_name)


@init_func(extension=Extensions.WEB)
async def init_controllers(context: blnt.BolinetteContext):
    def _init_ctrl(controller: web.Controller):
        def _init_route(_attr: blnt.InstantiableAttribute[web.ControllerRoute]):
            _route = _attr.instantiate(controller=controller)
            if _route.inner_route is not None:
                _route.inner_route, _route.func = _init_route(_route.inner_route)  # type: ignore
            return _route, _route.func

        for route_name, proxy in controller.__props__.get_instantiable(web.ControllerRoute):
            route, _ = _init_route(proxy)
            setattr(controller, route_name, route)
        for _, route in controller.__props__.get_routes():
            route.controller = controller
            route.setup()
        for route in controller.default_routes():
            route.controller = controller
            route.setup()

    for controller_name, controller_cls in blnt.cache.controllers.items():
        context.inject.register(controller_cls, 'controller', controller_name, func=_init_ctrl)


# @init_func(extension=Extensions.SOCKETS)
# async def init_topics(context: blnt.BolinetteContext):
#     for topic_name, topic_cls in blnt.cache.topics.items():
#         topic = topic_cls(context)
#         context.sockets.add_topic(topic_name, topic)
#         for _, channel in topic.__props__.get_channels():
#             context.sockets.add_channel(topic_name, channel)
