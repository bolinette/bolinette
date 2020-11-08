from bolinette import types, core
from bolinette.decorators import model


@model('file')
class File(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    key = types.defs.Column(types.db.String, nullable=False)
    name = types.defs.Column(types.db.String, nullable=False)
    mime = types.defs.Column(types.db.String, nullable=False)

    @classmethod
    def responses(cls):
        yield [
            types.mapping.Column(cls.key),
            types.mapping.Column(cls.name),
            types.mapping.Column(cls.mime)
        ]
        yield 'minimal', [
            types.mapping.Column(cls.key)
        ]
