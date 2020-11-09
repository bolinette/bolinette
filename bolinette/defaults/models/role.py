from bolinette import types, core, mapping
from bolinette.decorators import model


@model('role')
class Role(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, unique=True, nullable=False)

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
