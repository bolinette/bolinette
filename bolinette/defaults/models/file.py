from bolinette import types, core, mapping
from bolinette.decorators import model


@model('file')
class File(core.Model):
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
