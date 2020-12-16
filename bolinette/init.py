import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import blnt, core, web
from bolinette.decorators import init_func
from bolinette.exceptions import InitError


@init_func
def init_relational_models(context: blnt.BolinetteContext):
    models = {}
    for model_name, model_cls in blnt.cache.models.items():
        db_key = model_cls.__blnt__.database
        if db_key in context.db:
            if not context.db[db_key].relational:
                continue
            database = context.db[db_key]
        else:
            raise InitError(f'Undefined "{db_key}" database for model "{model_name}"')
        models[model_name] = model_cls(database)
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
                att_name, attribute.type.sqlalchemy_type, ref, default=attribute.default,
                primary_key=attribute.primary_key, nullable=attribute.nullable, unique=attribute.unique)
        orm_tables[model_name] = sqlalchemy.Table(model_name,
                                                  model.__props__.database.base.metadata,
                                                  *(orm_cols[model_name].values()))

    for model_name, model in models.items():
        orm_defs = {}
        for att_name, attribute in model.__props__.get_relationships().items():
            kwargs = {}
            attribute.name = att_name
            if attribute.backref:
                kwargs['backref'] = sqlalchemy_orm.backref(attribute.backref.key, lazy=attribute.backref.lazy)
            if attribute.foreign_key:
                kwargs['foreign_keys'] = orm_cols[model_name][attribute.foreign_key.name]
            if attribute.remote_side:
                kwargs['remote_side'] = orm_cols[model_name][attribute.remote_side.name]
            if attribute.secondary:
                kwargs['secondary'] = orm_tables[attribute.secondary]
            orm_defs[att_name] = sqlalchemy_orm.relationship(attribute.model_name,  lazy=attribute.lazy, **kwargs)

        orm_defs['__table__'] = orm_tables[model_name]
        orm_model = type(model_name, (model.__props__.database.base,), orm_defs)

        for att_name, attribute in model.__props__.get_properties().items():
            setattr(orm_model, att_name, property(attribute.function))

        context.add_model(model_name, model)
        context.add_table(model_name, orm_model)


@init_func
def init_collection_models(context: blnt.BolinetteContext):
    models = {}
    for model_name, model_cls in blnt.cache.models.items():
        db_key = model_cls.__blnt__.database
        if db_key in context.db:
            if context.db[db_key].relational:
                continue
            database = context.db[db_key]
        else:
            raise InitError(f'Undefined "{db_key}" database for model "{model_name}"')
        models[model_name] = model_cls(database)
    for model_name, model in models.items():
        for att_name, attribute in model.__props__.get_columns().items():
            attribute.name = att_name
        context.add_model(model_name, model)


@init_func
async def init_databases(context: blnt.BolinetteContext):
    await context.db.create_all()


@init_func
def init_repositories(context: blnt.BolinetteContext):
    for model_name, model in context.models:
        context.add_repo(model_name, core.Repository(model_name, model, context))


@init_func
def init_mappings(context: blnt.BolinetteContext):
    for model_name, model in context.models:
        context.mapper.register(model_name, model)


@init_func
def init_services(context: blnt.BolinetteContext):
    for service_name, service_cls in blnt.cache.services.items():
        context.add_service(service_name, service_cls(context))


@init_func
def init_controllers(context: blnt.BolinetteContext):
    for controller_name, controller_cls in blnt.cache.controllers.items():
        controller = controller_cls(context)
        for _, route in controller.__props__.get_routes():
            route.setup(controller)
        for route in controller.default_routes():
            route.setup(controller)
        context.add_controller(controller_name, controller)


@init_func
def init_topics(context: blnt.BolinetteContext):
    context.sockets.init_socket_handler()
    for topic_name, topic_cls in blnt.cache.topics.items():
        topic = topic_cls(context)
        context.sockets.add_topic(topic_name, topic)
        for channel_name, channel in topic.__props__.get_channels().items():
            context.sockets.add_channel(topic_name, channel)
