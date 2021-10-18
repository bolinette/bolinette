from bolinette import core, types, mapping
from bolinette.decorators import model


@model('label')
class Label(core.Model):
    tag_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('tag', 'id'), primary_key=True)
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, nullable=False)

    tag = types.defs.Relationship('tag', foreign_key="tag_id", lazy=True,
                                  backref=types.defs.Backref('labels', lazy=False))

    def responses(self):
        yield [
            mapping.Field(types.db.String, name='tag', function=lambda l: l.tag.name),
            mapping.Column(self.id),
            mapping.Column(self.name)
        ]
        yield 'complete', [
            mapping.Reference(self.tag),
            mapping.Column(self.id),
            mapping.Column(self.name)
        ]
