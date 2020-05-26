from bolinette import types, blnt
from bolinette.decorators import model


@model('person')
class Person(blnt.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    first_name = types.defs.Column(types.db.String, nullable=False)
    last_name = types.defs.Column(types.db.String, nullable=False)

    @classmethod
    def payloads(cls):
        yield [
            types.mapping.Column(cls.first_name, required=True),
            types.mapping.Column(cls.last_name, required=True)
        ]

    @classmethod
    def responses(cls):
        yield [
            types.mapping.Column(cls.first_name),
            types.mapping.Column(cls.last_name),
            types.mapping.Field(types.db.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}')
        ]
        yield 'complete', [
            types.mapping.Column(cls.first_name),
            types.mapping.Column(cls.last_name),
            types.mapping.Field(types.db.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}'),
            types.mapping.List(types.mapping.Definition('book'), key='books')
        ]
