from typing import Any

from bolinette import types
from bolinette.data import Model, model, mapping

from example.entities import Book


@model('book', mixins=['historized'])
class BookModel(Model[Book]):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    uid = types.defs.Column(types.db.String, unique=True, nullable=False, entity_key=True)
    name = types.defs.Column(types.db.String, nullable=False)
    pages = types.defs.Column(types.db.Integer, nullable=False)
    price = types.defs.Column(types.db.Float, nullable=False)
    publication_date = types.defs.Column(types.db.Date, nullable=False)

    author_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('person', 'id'), nullable=False)
    author = types.defs.Relationship('person', foreign_key="author_id", backref=types.defs.Backref('books'), lazy=False)

    def payloads(self):
        yield [
            mapping.Column(self.uid, required=True),
            mapping.Column(self.name, required=True),
            mapping.Column(self.pages, required=True),
            mapping.Column(self.price, required=True),
            mapping.Column(self.publication_date, required=True),
            mapping.Reference(self.author, required=True)
        ]

    def responses(self):
        base = self.get_mixin('historized').response(self)
        default: list[Any] = [
            mapping.Column(self.uid),
            mapping.Column(self.name),
            mapping.Column(self.pages),
            mapping.Column(self.price),
            mapping.Column(self.publication_date)
        ]
        yield default
        yield 'complete', default + [
            mapping.Reference(self.author)
        ] + base
