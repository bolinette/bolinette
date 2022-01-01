from bolinette import types, data
from bolinette.data import ext, mapping


@ext.model('file')
class File(data.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    key = types.defs.Column(types.db.String, nullable=False, unique=True, entity_key=True)
    name = types.defs.Column(types.db.String, nullable=False)
    mime = types.defs.Column(types.db.String, nullable=False)

    def responses(self):
        yield [
            mapping.Column(self.key),
            mapping.Column(self.name),
            mapping.Column(self.mime)
        ]
        yield 'minimal', [
            mapping.Column(self.key)
        ]