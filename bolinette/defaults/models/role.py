from bolinette import mapping, db, data
from bolinette.decorators import model


@model('role')
class Role(data.Model):
    id = db.defs.Column(db.types.Integer, primary_key=True)
    name = db.defs.Column(db.types.String, unique=True, nullable=False)

    @classmethod
    def payloads(cls):
        yield [
            mapping.Column(cls.name, required=True)
        ]

    @classmethod
    def responses(cls):
        yield [
            mapping.Column(cls.name)
        ]
        yield 'complete', [
            mapping.Column(cls.name),
            mapping.List(mapping.Definition('user'), key='users')
        ]
