import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import core, data
from bolinette.decorators import init_func


@init_func
def init_models(context: core.BolinetteContext):
    models = {}
    for model_name, model_cls in core.cache.models.items():
        models[model_name] = model_cls(model_name)
    orm_tables = {}
    for model_name, model in models.items():
        for att_name, attribute in model.__blnt__.get_columns().items():
            attribute.name = att_name
            ref = None
            if attribute.reference:
                ref = sqlalchemy.ForeignKey(f'{attribute.reference.model_name}.{attribute.reference.column_name}')
            model.__blnt__.orm_columns[att_name] = sqlalchemy.Column(att_name, attribute.type.sqlalchemy_type, ref,
                                                                     primary_key=attribute.primary_key,
                                                                     nullable=attribute.nullable,
                                                                     unique=attribute.unique)
        orm_tables[model_name] = sqlalchemy.Table(model_name,
                                                  context.db.model.metadata,
                                                  *(model.__blnt__.orm_columns.values()))

    for model_name, model in models.items():
        orm_defs = {}
        for att_name, attribute in model.__blnt__.get_relationships().items():
            attribute.name = att_name
            backref = None
            if attribute.backref:
                backref = sqlalchemy_orm.backref(attribute.backref.key, lazy=attribute.backref.lazy)
            foreign_key = None
            if attribute.foreign_key:
                foreign_key = model.__blnt__.orm_columns[attribute.foreign_key.name]
            secondary = None
            if attribute.secondary:
                secondary = orm_tables[attribute.secondary]
            orm_def = sqlalchemy_orm.relationship(attribute.model_name, secondary=secondary,
                                                  lazy=attribute.lazy, foreign_keys=foreign_key,
                                                  backref=backref)
            orm_defs[att_name] = orm_def

        orm_defs['__table__'] = orm_tables[model_name]
        orm_model = type(model_name, (context.db.model,), orm_defs)

        for att_name, attribute in model.__blnt__.get_properties().items():
            setattr(orm_model, att_name, property(attribute.function))

        model.__blnt__.orm_model = orm_model
        context.models[model_name] = model
        context.tables[model_name] = orm_model


@init_func
def init_repositories(context: core.BolinetteContext):
    for model_name, model in context.models.items():
        context.repos[model_name] = data.Repository(model_name, model, context.db)
