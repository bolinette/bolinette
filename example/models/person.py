from bolinette import mapping, db, data
from bolinette.decorators import model


@model('person')
class Person(data.Model):
    id = db.defs.Column(db.types.Integer, primary_key=True)
    first_name = db.defs.Column(db.types.String, nullable=False)
    last_name = db.defs.Column(db.types.String, nullable=False)

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
            mapping.Field(db.types.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}')
        ]
        yield 'complete', [
            mapping.Column(cls.first_name),
            mapping.Column(cls.last_name),
            mapping.Field(db.types.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}'),
            mapping.List(mapping.Definition('book'), key='books')
        ]
