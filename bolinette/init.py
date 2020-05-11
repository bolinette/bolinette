import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import core
from bolinette.decorators import init_func


@init_func
def init_models(context):
    orm_tables = {}
    for model_name, model_cls in core.cache.models.items():
        orm_cols = []
        for att_name, attribute in model_cls.get_columns().items():
            attribute.name = att_name
            attribute.model = model_cls
            ref = None
            if attribute.reference:
                ref = sqlalchemy.ForeignKey(
                    f'{attribute.reference.model_name}.{attribute.reference.column_name}')
            attribute.orm_def = sqlalchemy.Column(att_name, attribute.type.sqlalchemy_type, ref,
                                                  primary_key=attribute.primary_key,
                                                  nullable=attribute.nullable,
                                                  unique=attribute.unique)
            orm_cols.append(attribute.orm_def)
        orm_tables[model_name] = sqlalchemy.Table(model_name, context.db.model.metadata, *orm_cols)

    for model_name, model_cls in core.cache.models.items():
        orm_relationships = []
        for att_name, attribute in model_cls.get_relationships().items():
            attribute.name = att_name
            attribute.model = model_cls
            backref = None
            if attribute.backref:
                backref = sqlalchemy_orm.backref(attribute.backref.key, lazy=attribute.backref.lazy)
            foreign_key = None
            if attribute.foreign_key:
                foreign_key = attribute.foreign_key.orm_def
            secondary = None
            if attribute.secondary:
                secondary = orm_tables[attribute.secondary]
            attribute.orm_def = sqlalchemy_orm.relationship(attribute.model_name, secondary=secondary,
                                                            lazy=attribute.lazy, foreign_keys=foreign_key,
                                                            backref=backref)
            orm_relationships.append(attribute)

        orm_defs = dict([(c.name, c.orm_def) for c in orm_relationships])
        orm_defs['__table__'] = orm_tables[model_name]
        orm_model = type(model_name, (context.db.model,), orm_defs)

        for att_name, attribute in model_cls.get_properties().items():
            setattr(orm_model, att_name, property(attribute.function))

        setattr(core.cache.models[model_name], '__orm_model__', orm_model)
        setattr(core.cache.models[model_name], '__model_name__', model_name)
