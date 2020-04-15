from typing import Dict, Type

import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import db


class Models:
    def __init__(self):
        self.registered: Dict[str, Type['db.defs.Model']] = {}

    def get(self, name: str) -> Type['db.defs.Model']:
        return self.registered.get(name, None)

    def register(self, model_name: str, model_cls: Type['db.defs.Model']):
        self.registered[model_name] = model_cls

    def init_models(self):
        orm_tables = {}
        for model_name, model_cls in self.registered.items():
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
            orm_tables[model_name] = sqlalchemy.Table(model_name, db.engine.model.metadata, *orm_cols)

        for model_name, model_cls in self.registered.items():
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
            orm_model = type(model_name, (db.engine.model,), orm_defs)

            for att_name, attribute in model_cls.get_properties().items():
                setattr(orm_model, att_name, property(attribute.function))

            setattr(self.registered[model_name], '__orm_model__', orm_model)
            setattr(self.registered[model_name], '__model_name__', model_name)


models = Models()
