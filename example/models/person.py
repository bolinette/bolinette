from bolinette import types, core, mapping
from bolinette.decorators import model


@model('person')
class Person(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    first_name = types.defs.Column(types.db.String, nullable=False)
    last_name = types.defs.Column(types.db.String, nullable=False)

    @classmethod
    def payloads(cls):
        yield [
            mapping.Column(cls.first_name, required=True),
            mapping.Column(cls.last_name, required=True)
        ]

    @classmethod
    def responses(cls):
        yield [
            mapping.Column(cls.first_name),
            mapping.Column(cls.last_name),
            mapping.Field(types.db.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}')
        ]
        yield 'complete', [
            mapping.Column(cls.first_name),
            mapping.Column(cls.last_name),
            mapping.Field(types.db.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}'),
            mapping.List(mapping.Definition('book'), key='books')
        ]
