import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import core, blnt
from bolinette.decorators import init_func


@init_func
def init_models(context: core.BolinetteContext):
    models = {}
    for model_name, model_cls in core.cache.models.items():
        models[model_name] = model_cls()
    orm_tables = {}
    orm_cols = {}
    for model_name, model in models.items():
        orm_cols[model_name] = {}
        for att_name, attribute in model.__props__.get_columns().items():
            attribute.name = att_name
            ref = None
            if attribute.reference:
                ref = sqlalchemy.ForeignKey(f'{attribute.reference.model_name}.{attribute.reference.column_name}')
            orm_cols[model_name][att_name] = sqlalchemy.Column(
                att_name, attribute.type.sqlalchemy_type, ref,
                primary_key=attribute.primary_key, nullable=attribute.nullable, unique=attribute.unique)
        orm_tables[model_name] = sqlalchemy.Table(model_name,
                                                  context.db.model.metadata,
                                                  *(orm_cols[model_name].values()))

    for model_name, model in models.items():
        orm_defs = {}
        for att_name, attribute in model.__props__.get_relationships().items():
            attribute.name = att_name
            backref = None
            if attribute.backref:
                backref = sqlalchemy_orm.backref(attribute.backref.key, lazy=attribute.backref.lazy)
            foreign_key = None
            if attribute.foreign_key:
                foreign_key = orm_cols[model_name][attribute.foreign_key.name]
            secondary = None
            if attribute.secondary:
                secondary = orm_tables[attribute.secondary]
            orm_defs[att_name] = sqlalchemy_orm.relationship(attribute.model_name, secondary=secondary,
                                                             lazy=attribute.lazy, foreign_keys=foreign_key,
                                                             backref=backref)

        orm_defs['__table__'] = orm_tables[model_name]
        orm_model = type(model_name, (context.db.model,), orm_defs)

        for att_name, attribute in model.__props__.get_properties().items():
            setattr(orm_model, att_name, property(attribute.function))

        context.add_model(model_name, model)
        context.add_table(model_name, orm_model)


@init_func
def init_repositories(context: core.BolinetteContext):
    for model_name, model in context.models:
        context.add_repo(model_name, blnt.Repository(model_name, model, context))


@init_func
def init_mappings(context: core.BolinetteContext):
    for model_name, model in context.models:
        context.mapping.register(model_name, model)


@init_func
def init_services(context: core.BolinetteContext):
    for service_name, service_cls in core.cache.services.items():
        context.add_service(service_name, service_cls(context))


@init_func
def init_controllers(context: core.BolinetteContext):
    for controller_name, controller_cls in core.cache.controllers.items():
        controller = controller_cls(context)
        base_path = '/api' if controller.__blnt__.api else ''
        for _, route in controller.__props__.get_routes().items():
            path = f'{base_path}{controller.__blnt__.path}{route.path}'
            context.resources.add_route(path, controller, route)
        if isinstance(controller, blnt.Controller):
            for route in controller.default_routes():
                path = f'{base_path}{controller.__blnt__.path}{route.path}'
                context.resources.add_route(path, controller, route)
        context.add_controller(controller_name, controller)


@init_func
def init_static_controller(context: core.BolinetteContext):
    controller = blnt.StaticController(context)
    for _, route in controller.__props__.get_routes().items():
        context.resources.add_route(route.path, controller, route)


@init_func
def init_topics(context: core.BolinetteContext):
    context.sockets.init_socket_handler()
    for topic_name, topic_cls in core.cache.topics.items():
        topic = topic_cls(context)
        context.sockets.add_topic(topic_name, topic)
        for channel_name, channel in topic.__props__.get_channels().items():
            context.sockets.add_channel(topic_name, channel)
