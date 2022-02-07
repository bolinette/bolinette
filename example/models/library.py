from bolinette import types
from bolinette.data import Model, model, mapping

from example.entities import Library


@model("library", database="mongo")
class LibraryModel(Model[Library]):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    key = types.defs.Column(
        types.db.String, nullable=False, unique=True, entity_key=True
    )
    name = types.defs.Column(types.db.String, nullable=False)
    address = types.defs.Column(types.db.String)

    def payloads(self):
        yield [
            mapping.Column(self.key, required=True),
            mapping.Column(self.name, required=True),
            mapping.Column(self.address),
        ]

    def responses(self):
        yield [
            mapping.Column(self.key),
            mapping.Column(self.name),
            mapping.Column(self.address),
        ]
