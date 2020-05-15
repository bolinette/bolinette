from bolinette import mapping, types, data
from bolinette.decorators import model


@model('file')
class File(data.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    key = types.defs.Column(types.db.String, nullable=False)
    name = types.defs.Column(types.db.String, nullable=False)
    mime = types.defs.Column(types.db.String, nullable=False)

    @classmethod
    def responses(cls):
        yield [
            mapping.Column(cls.key),
            mapping.Column(cls.name),
            mapping.Column(cls.mime)
        ]
        yield 'minimal', [
            mapping.Column(cls.key)
        ]
