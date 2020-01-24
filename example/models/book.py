from bolinette import db, marshalling


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('people.id'), nullable=False)
    author = db.relationship('Person', foreign_keys='Book.author_id',
                             backref='books', lazy=False)

    @staticmethod
    def payloads():
        yield 'default', [
            marshalling.Field(marshalling.types.string, 'name', required=True),
            marshalling.Field(marshalling.types.integer, 'pages', required=True),
            marshalling.Field(marshalling.types.foreign_key('person', 'id'),
                              'author_id', required=True)
        ]

    @staticmethod
    def responses():
        yield 'default', [
            marshalling.Field(marshalling.types.string, 'name', required=True),
            marshalling.Field(marshalling.types.integer, 'pages', required=True)
        ]
        yield 'complete', [
            marshalling.Field(marshalling.types.string, 'name', required=True),
            marshalling.Field(marshalling.types.integer, 'pages', required=True),
            marshalling.Definition('author', 'person', 'default')
        ]


marshalling.register(Book, 'book')
