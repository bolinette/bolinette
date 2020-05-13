from bolinette import mapping, types, data
from bolinette.decorators import model


@model('file')
class File(data.Model):
    id = types.Column(types.Integer, primary_key=True)
    key = types.Column(types.String, nullable=False)
    name = types.Column(types.String, nullable=False)
    mime = types.Column(types.String, nullable=False)

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
