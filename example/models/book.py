from bolinette import mapping, db
from bolinette.models import Historized


@db.model('book')
class Book(Historized):
    id = db.types.Column(db.types.Integer, primary_key=True)
    name = db.types.Column(db.types.String, nullable=False)
    pages = db.types.Column(db.types.Integer, nullable=False)
    price = db.types.Column(db.types.Float, nullable=False)
    publication_date = db.types.Column(db.types.Date, nullable=False)

    author_id = db.types.Column(db.types.Integer, reference=db.types.Reference('person', 'id'), nullable=False)
    author = db.types.Relationship('person', foreign_key=author_id, backref=db.types.Backref('books'), lazy=False)

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
        base = Historized.base_response()
        default: db.types.MappingPyTyping = [
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
