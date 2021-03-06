from bolinette import core, types, mapping
from bolinette.decorators import model


@model('library', database='mongo')
class Library(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    key = types.defs.Column(types.db.String, nullable=False, unique=True, model_id=True)
    name = types.defs.Column(types.db.String, nullable=False)
    address = types.defs.Column(types.db.String)

    def payloads(self):
        yield [
            mapping.Column(self.key, required=True),
            mapping.Column(self.name, required=True),
            mapping.Column(self.address)
        ]

    def responses(self):
        yield [
            mapping.Column(self.key),
            mapping.Column(self.name),
            mapping.Column(self.address)
        ]
