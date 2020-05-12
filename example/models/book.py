from bolinette import mapping, db, data
from bolinette.decorators import model


@model('book')
@db.with_mixin('historized')
class Book(data.Model):
    id = db.defs.Column(db.types.Integer, primary_key=True)
    name = db.defs.Column(db.types.String, nullable=False)
    pages = db.defs.Column(db.types.Integer, nullable=False)
    price = db.defs.Column(db.types.Float, nullable=False)
    publication_date = db.defs.Column(db.types.Date, nullable=False)

    author_id = db.defs.Column(db.types.Integer, reference=db.defs.Reference('person', 'id'), nullable=False)
    author = db.defs.Relationship('person', foreign_key=author_id, backref=db.defs.Backref('books'), lazy=False)

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
        base = db.mixins.get('historized').response(cls)
        default = [
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
