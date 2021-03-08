from bolinette import core, types, mapping
from bolinette.decorators import model


@model('tag')
class Tag(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, nullable=False, unique=True, model_id=True)

    parent_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('tag', 'id'))
    parent = types.defs.Relationship('tag', remote_side=id, lazy=True,
                                     backref=types.defs.Backref('children', lazy=False))

    def payloads(self):
        yield [
            mapping.Column(self.name, required=True),
        ]

    def responses(self):
        yield [
            mapping.Column(self.name)
        ]
        yield 'complete', [
            mapping.Column(self.name),
            mapping.List(mapping.Definition('tag', 'complete'), key='children')
        ]
