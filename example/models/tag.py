from bolinette import core, types, mapping
from bolinette.decorators import model


@model('tag')
class Tag(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, nullable=False)

    parent_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('tag', 'id'))
    parent = types.defs.Relationship('tag', remote_side=id, lazy=True,
                                     backref=types.defs.Backref('children', lazy=False))

    @classmethod
    def payloads(cls):
        yield [
            mapping.Column(cls.name, required=True),
        ]

    @classmethod
    def responses(cls):
        yield [
            mapping.Column(cls.name)
        ]
        yield 'complete', [
            mapping.Column(cls.name),
            mapping.List(mapping.Definition('tag', 'complete'), key='children')
        ]
