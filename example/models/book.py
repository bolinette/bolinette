from bolinette import mapping, db
from bolinette.models import Historized
from example.models import Person


class Book(db.defs.model, Historized):
    __tablename__ = 'book'

    id = db.defs.column(db.types.integer, primary_key=True)
    name = db.defs.column(db.types.string, nullable=False)
    pages = db.defs.column(db.types.integer, nullable=False)
    price = db.defs.column(db.types.float, nullable=False)
    publication_date = db.defs.column(db.types.date, nullable=False)

    author_id = db.defs.column(db.types.integer, db.types.foreign_key('person', 'id'), nullable=False)
    author = db.defs.relationship(Person, foreign_keys=author_id, backref='books', lazy=False)

    @staticmethod
    def payloads():
        yield [
            mapping.Field(db.types.string, key='name', required=True),
            mapping.Field(db.types.integer, key='pages', required=True),
            mapping.Field(db.types.float, key='price', required=True),
            mapping.Field(db.types.date, key='publication_date', required=True),
            mapping.Field(db.types.foreign_key('person', 'id'), key='author_id', required=True)
        ]

    @staticmethod
    def responses():
        base = Historized.base_response()
        yield [
            mapping.Field(db.types.integer, key='id'),
            mapping.Field(db.types.string, key='name'),
            mapping.Field(db.types.integer, key='pages'),
            mapping.Field(db.types.float, key='price'),
            mapping.Field(db.types.date, key='publication_date')
        ]
        yield 'complete', [
            mapping.Field(db.types.integer, key='id'),
            mapping.Field(db.types.string, key='name'),
            mapping.Field(db.types.integer, key='pages'),
            mapping.Field(db.types.float, key='price'),
            mapping.Field(db.types.date, key='publication_date'),
            mapping.Definition('person', key='author')
        ] + base


mapping.register(Book)
