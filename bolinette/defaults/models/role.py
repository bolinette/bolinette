from bolinette import types, blnt
from bolinette.decorators import model


@model('role')
class Role(blnt.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, unique=True, nullable=False)

    @classmethod
    def payloads(cls):
        yield [
            types.mapping.Column(cls.name, required=True)
        ]

    @classmethod
    def responses(cls):
        yield [
            types.mapping.Column(cls.name)
        ]
        yield 'complete', [
            types.mapping.Column(cls.name),
            types.mapping.List(types.mapping.Definition('user'), key='users')
        ]
