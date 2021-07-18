import typing as _typing

from bolinette import types, core, mapping
from bolinette.decorators import model, model_property


@model('person', mixins=['historized'])
class Person(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    uid = types.defs.Column(types.db.String, nullable=False, unique=True, entity_key=True)
    first_name = types.defs.Column(types.db.String, nullable=False)
    last_name = types.defs.Column(types.db.String, nullable=False)

    @model_property
    def last_book(self):
        if len(self.books):
            return sorted(self.books, key=lambda b: b.publication_date, reverse=True)[0]
        return None

    def payloads(self):
        yield [
            mapping.Column(self.uid, required=True),
            mapping.Column(self.first_name, required=True),
            mapping.Column(self.last_name, required=True)
        ]

    def responses(self):
        base: _typing.List[_typing.Any] = [
            mapping.Column(self.uid),
            mapping.Column(self.first_name),
            mapping.Column(self.last_name),
            mapping.Field(types.db.String, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}')
        ]
        yield base
        yield 'complete', base + [
            mapping.List(mapping.Definition('book'), key='books'),
            mapping.Definition('book', key='last_book')
        ]
