import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import blnt, core, web
from bolinette.decorators import init_func


@init_func
def init_models(context: blnt.BolinetteContext):
    models = {}
    for model_name, model_cls in blnt.cache.models.items():
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
                att_name, attribute.type.sqlalchemy_type, ref, default=attribute.default,
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
    def _init_sys_middleware(_route: 'web.ControllerRoute'):
        sys_mdw = []
        if _route.expects is not None:
            model = _route.expects.model
            key = _route.expects.key if _route.expects.key is not None else 'default'
            cmd = f'blnt_payload|model:{model}|key:{key}'
            if _route.expects.patch:
                cmd += '|patch'
            sys_mdw.append(cmd)
        else:
            sys_mdw.append('blnt_payload')
        if _route.returns is not None:
            model = _route.returns.model
            key = _route.returns.key if _route.returns.key is not None else 'default'
            cmd = f'blnt_response|model:{model}|key:{key}'
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
