from bolinette import db, mapping


class Book(db.types.Model):
    __tablename__ = 'books'

    id = db.types.Column(db.types.Integer, primary_key=True)
    name = db.types.Column(db.types.String, nullable=False)
    pages = db.types.Column(db.types.Integer, nullable=False)
    author_id = db.types.Column(db.types.Integer, db.types.ForeignKey('people.id'), nullable=False)
    author = db.types.relationship('Person', foreign_keys='Book.author_id',
                                   backref='books', lazy=False)

    @staticmethod
    def payloads():
        yield [
            mapping.Field(mapping.types.string, 'name', required=True),
            mapping.Field(mapping.types.integer, 'pages', required=True),
            mapping.Field(mapping.types.foreign_key('person', 'id'),
                          'author_id', required=True)
        ]

    @staticmethod
    def responses():
        yield [
            mapping.Field(mapping.types.integer, 'id', required=True),
            mapping.Field(mapping.types.string, 'name', required=True),
            mapping.Field(mapping.types.integer, 'pages', required=True)
        ]
        yield 'complete', [
            mapping.Field(mapping.types.integer, 'id', required=True),
            mapping.Field(mapping.types.string, 'name', required=True),
            mapping.Field(mapping.types.integer, 'pages', required=True),
            mapping.Definition('author', 'person')
        ]


mapping.register(Book, 'book')
