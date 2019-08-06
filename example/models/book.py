from bolinette import db, marshalling


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner = db.relationship('User', foreign_keys='Book.owner_id', backref='books')

    @staticmethod
    def payloads():
        yield 'default', [
            marshalling.Field('name', required=True),
            marshalling.Field('owner_id', required=True)
        ]

    @staticmethod
    def responses():
        yield 'default', [
            marshalling.Field('name', required=True)
        ]
        yield 'complete', [
            marshalling.Field('name', required=True),
            marshalling.Definition('owner', 'user.public')
        ]


marshalling.register(Book, 'book')
