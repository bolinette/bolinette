from bolinette import mapping, db


@db.mixin('historized')
class Historized(db.defs.Mixin):
    @staticmethod
    def columns():
        return {
            'created_on': db.defs.Column(db.types.Date),
            'updated_on': db.defs.Column(db.types.Date),
            'created_by_id': db.defs.Column(db.types.Integer, reference=db.defs.Reference('user', 'id')),
            'updated_by_id': db.defs.Column(db.types.Integer, reference=db.defs.Reference('user', 'id'))
        }

    @staticmethod
    def relationships(model_cls):
        return {
            'created_by': db.defs.Relationship('user', foreign_key=model_cls.created_by_id, lazy=False),
            'updated_by': db.defs.Relationship('user', foreign_key=model_cls.updated_by_id, lazy=False)
        }

    @staticmethod
    def response(model_cls):
        return [
            mapping.Column(model_cls.created_on),
            mapping.Column(model_cls.updated_on),
            mapping.Reference(model_cls.created_by),
            mapping.Reference(model_cls.updated_by),
        ]
