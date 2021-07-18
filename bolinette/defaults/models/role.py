from bolinette import types, core, mapping
from bolinette.decorators import model


@model('role')
class Role(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, unique=True, nullable=False, entity_key=True)

    def payloads(self):
        yield [
            mapping.Column(self.name, required=True)
        ]

    def responses(self):
        yield [
            mapping.Column(self.name)
        ]
        yield 'complete', [
            mapping.Column(self.name),
            mapping.List(mapping.Definition('user'), key='users')
        ]
