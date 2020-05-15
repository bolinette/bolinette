from typing import Any, List

from bolinette import mapping, types, data, core
from bolinette.decorators import model, with_mixin


@model('book')
@with_mixin('historized')
class Book(data.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, nullable=False)
    pages = types.defs.Column(types.db.Integer, nullable=False)
    price = types.defs.Column(types.db.Float, nullable=False)
    publication_date = types.defs.Column(types.db.Date, nullable=False)

    author_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('person', 'id'), nullable=False)
    author = types.defs.Relationship('person', foreign_key=author_id, backref=types.defs.Backref('books'), lazy=False)

    @classmethod
    def payloads(cls):
        yield [
            mapping.Column(cls.name, required=True),
            mapping.Column(cls.pages, required=True),
            mapping.Column(cls.price, required=True),
            mapping.Column(cls.publication_date, required=True),
            mapping.Reference(cls.author,  required=True)
        ]

    @classmethod
    def responses(cls):
        base = core.cache.mixins.get('historized').response(cls)
        default: List[Any] = [
            mapping.Column(cls.id),
            mapping.Column(cls.name),
            mapping.Column(cls.pages),
            mapping.Column(cls.price),
            mapping.Column(cls.publication_date)
        ]
        yield default
        yield 'complete', default + [
            mapping.Reference(cls.author)
        ] + base
