from bolinette import core, types, mapping
from bolinette.decorators import model


@model('library', database='mongo')
class Library(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    key = types.defs.Column(types.db.String, nullable=False, unique=True)
    name = types.defs.Column(types.db.String, nullable=False)
    address = types.defs.Column(types.db.String)

    @classmethod
    def payloads(cls):
        yield [
            mapping.Column(cls.key, required=True),
            mapping.Column(cls.name, required=True),
            mapping.Column(cls.address)
        ]

    @classmethod
    def responses(cls):
        yield [
            mapping.Column(cls.key),
            mapping.Column(cls.name),
            mapping.Column(cls.address)
        ]
