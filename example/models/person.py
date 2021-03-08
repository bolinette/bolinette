from bolinette import types, core, mapping
from bolinette.decorators import model


@model('person')
class Person(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    uid = types.defs.Column(types.db.String, nullable=False, unique=True, model_id=True)
    first_name = types.defs.Column(types.db.String, nullable=False)
    last_name = types.defs.Column(types.db.String, nullable=False)

    def payloads(self):
        yield [
            mapping.Column(self.first_name, required=True),
            mapping.Column(self.last_name, required=True)
        ]

    def responses(self):
        yield [
            mapping.Column(self.first_name),
            mapping.Column(self.last_name),
            mapping.Field(types.db.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}')
        ]
        yield 'complete', [
            mapping.Column(self.first_name),
            mapping.Column(self.last_name),
            mapping.Field(types.db.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}'),
            mapping.List(mapping.Definition('book'), key='books')
        ]
