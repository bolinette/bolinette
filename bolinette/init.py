from typing import Dict, List

import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import blnt, core, web, Extensions
from bolinette.decorators import init_func
from bolinette.exceptions import InitError
from bolinette.utils import InitProxy


@init_func(extension=Extensions.MODELS)
async def init_model_classes(context: blnt.BolinetteContext):
    models = {}
    proxies = {}
    for model_name, model_cls in blnt.cache.models.items():
        db_key = model_cls.__blnt__.database
        if db_key not in context.db:
            raise InitError(f'Undefined "{db_key}" database for model "{model_name}"')
        model = model_cls(context.db[db_key])
        for col_name, proxy in model.__props__.get_proxies(core.models.Column):
            col = proxy.instantiate(name=col_name, model=model)
            proxies[proxy] = col
            setattr(model, col_name, col)
        for mixin_name in model.__blnt__.mixins:
            if mixin_name not in blnt.cache.mixins:
                raise InitError(f'Model "{model_name}": mixin "{mixin_name}" is not defined')
            mixin = blnt.cache.mixins[mixin_name]()
            for col_name, proxy in mixin.columns().items():
                col = proxy.instantiate(name=col_name, model=model)
                setattr(model, col_name, col)
            model.__props__.mixins[mixin_name] = mixin
        models[model_name] = model
    for model_name, model in models.items():
        for rel_name, proxy in model.__props__.get_proxies(core.models.Relationship):
            rel = proxy.instantiate(name=rel_name, model=model, models=models)
            proxies[proxy] = rel
            setattr(model, rel_name, rel)
        for _, mixin in model.__props__.mixins.items():
            for rel_name, proxy in mixin.relationships(model).items():
                rel = proxy.instantiate(name=rel_name, model=model, models=models)
                setattr(model, rel_name, rel)
    for model_name, model in models.items():
        for col_name, col in model.__props__.get_columns():
            if isinstance(col.reference, InitProxy) and col.reference.of_type(core.models.Reference):
                col.reference = col.reference.instantiate(model=model, column=col, models=models)
        added_back_refs: Dict[core.Model, List[core.models.ColumnList]] = {}
        for rel_name, rel in model.__props__.get_relationships():
            if isinstance(rel.backref, InitProxy) and rel.backref.of_type(core.models.Backref):
                rel.backref = rel.backref.instantiate(model=model, relationship=rel)
                if rel.backref.key not in added_back_refs:
                    added_back_refs[rel.target_model] = []
                added_back_refs[rel.target_model].append(
                    core.models.ColumnList(rel.backref.key, rel.target_model, model))
            if isinstance(rel.foreign_key, InitProxy) and rel.foreign_key.of_type(core.models.Column):
                rel.foreign_key = proxies[rel.foreign_key]
            if isinstance(rel.remote_side, InitProxy) and rel.remote_side.of_type(core.models.Column):
                rel.remote_side = proxies[rel.remote_side]
        for target_model, back_refs in added_back_refs.items():
            for back_ref in back_refs:
                setattr(target_model, back_ref.name, back_ref)
    for model_name, model in models.items():
        context.add_model(model_name, model)


@init_func(extension=Extensions.MODELS)
async def init_relational_models(context: blnt.BolinetteContext):
    models = {}
    for model_name, model in context.models:
        if model.__props__.database.relational:
            models[model_name] = model
    orm_tables = {}
    orm_cols = {}
    for model_name, model in models.items():
        orm_cols[model_name] = {}
        for att_name, attribute in model.__props__.get_columns():
            attribute.name = att_name
            ref = None
            if attribute.reference:
                ref = sqlalchemy.ForeignKey(attribute.reference.target_path)
            orm_cols[model_name][att_name] = sqlalchemy.Column(
                att_name, attribute.type.sqlalchemy_type, ref, default=attribute.default, index=attribute.model_id,
                primary_key=attribute.primary_key, nullable=attribute.nullable, unique=attribute.unique)
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

        context.add_table(model_name, orm_model)


@init_func(extension=Extensions.MODELS)
async def init_databases(context: blnt.BolinetteContext):
    await context.db.create_all()


@init_func(extension=Extensions.MODELS)
async def init_repositories(context: blnt.BolinetteContext):
    for model_name, model in context.models:
        context.add_repo(model_name, core.Repository(model_name, model, context))


@init_func(extension=Extensions.MODELS)
async def init_mappings(context: blnt.BolinetteContext):
    for model_name, model in context.models:
        context.mapper.register(model_name, model)


@init_func(extension=Extensions.MODELS)
async def init_services(context: blnt.BolinetteContext):
    for service_name, service_cls in blnt.cache.services.items():
        context.add_service(service_name, service_cls(context))


@init_func(extension=Extensions.WEB)
async def init_controllers(context: blnt.BolinetteContext):
    def _init_route(_ctrl: web.Controller, _proxy: InitProxy):
        _route = _proxy.instantiate(controller=_ctrl)
        if _route.inner_route is not None:
            _route.inner_route, _route.func = _init_route(_ctrl, _route.inner_route)
        return _route, _route.func

    for controller_name, controller_cls in blnt.cache.controllers.items():
        controller = controller_cls(context)
        for route_name, proxy in controller.__props__.get_proxies(web.ControllerRoute):
            route, _ = _init_route(controller, proxy)
            setattr(controller, route_name, route)
        for _, route in controller.__props__.get_routes():
            route.controller = controller
            route.setup()
        for route in controller.default_routes():
            route.controller = controller
            route.setup()
        context.add_controller(controller_name, controller)


@init_func(extension=Extensions.SOCKETS)
async def init_topics(context: blnt.BolinetteContext):
    for topic_name, topic_cls in blnt.cache.topics.items():
        topic = topic_cls(context)
        context.sockets.add_topic(topic_name, topic)
        for _, channel in topic.__props__.get_channels():
            context.sockets.add_channel(topic_name, channel)
