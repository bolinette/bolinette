from bolinette import types, core, mapping
from bolinette.decorators import mixin


@mixin('historized')
class Historized(core.Mixin):
    @staticmethod
    def columns():
        return {
            'created_on': types.defs.Column(types.db.Date),
            'updated_on': types.defs.Column(types.db.Date),
            'created_by_id': types.defs.Column(types.db.Integer, reference=types.defs.Reference('user', 'id')),
            'updated_by_id': types.defs.Column(types.db.Integer, reference=types.defs.Reference('user', 'id'))
        }

    @staticmethod
    def relationships(model_cls):
        return {
            'created_by': types.defs.Relationship('user', foreign_key=model_cls.created_by_id, lazy=False),
            'updated_by': types.defs.Relationship('user', foreign_key=model_cls.updated_by_id, lazy=False)
        }

    @staticmethod
    def response(model_cls):
        return [
            mapping.Column(model_cls.created_on),
            mapping.Column(model_cls.updated_on),
            mapping.Reference(model_cls.created_by),
            mapping.Reference(model_cls.updated_by),
        ]
