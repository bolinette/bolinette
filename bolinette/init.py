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
def init_repositories(context: blnt.BolinetteContext):
    for model_name, model in context.models:
        if model.__props__.database.relational:
            context.add_repo(model_name, core.RelationalRepository(model_name, model, context))
        else:
            context.add_repo(model_name, core.CollectionRepository(model_name, model, context))


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
    def _init_sys_middleware(_route: 'web.ControllerRoute'):
        sys_mdw = []
        if _route.expects is not None:
            model = _route.expects.model
            key = _route.expects.key if _route.expects.key is not None else 'default'
            cmd = f'blnt_payload|model={model}|key={key}'
            if _route.expects.patch:
                cmd += '|patch'
            sys_mdw.append(cmd)
        else:
            sys_mdw.append('blnt_payload')
        if _route.returns is not None:
            model = _route.returns.model
            key = _route.returns.key if _route.returns.key is not None else 'default'
            cmd = f'blnt_response|model={model}|key={key}'
            if _route.returns.as_list:
                cmd += '|as_list'
            if _route.returns.skip_none:
                cmd += '|skip_none'
            sys_mdw.append(cmd)
        else:
            sys_mdw.append('blnt_response')
        return sys_mdw

    def _add_route(_controller: web.Controller, _route: web.ControllerRoute):
        path = f'{_controller.__blnt__.namespace}{_controller.__blnt__.path}{_route.path}'
        _route.controller = _controller
        _route.init_middlewares(context, _controller.__blnt__.middlewares, _init_sys_middleware(_route))
        context.resources.add_route(path, _controller, _route)
        if _route.inner_route is not None:
            _add_route(_controller, _route.inner_route)

    for controller_name, controller_cls in blnt.cache.controllers.items():
        controller = controller_cls(context)
        for _, route in controller.__props__.get_routes().items():
            _add_route(controller, route)
        if isinstance(controller, web.Controller):
            for route in controller.default_routes():
                _add_route(controller, route)
        context.add_controller(controller_name, controller)


@init_func
def init_topics(context: blnt.BolinetteContext):
    context.sockets.init_socket_handler()
    for topic_name, topic_cls in blnt.cache.topics.items():
        topic = topic_cls(context)
        context.sockets.add_topic(topic_name, topic)
        for channel_name, channel in topic.__props__.get_channels().items():
            context.sockets.add_channel(topic_name, channel)
