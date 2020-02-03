from bolinette import db, marshalling


class Person(db.Model):
    __tablename__ = 'people'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    @staticmethod
    def payloads():
        yield [
            marshalling.Field(marshalling.types.string, 'name', required=True)
        ]

    @staticmethod
    def responses():
        yield [
            marshalling.Field(marshalling.types.string, 'name', required=True)
        ]
        yield 'complete', [
            marshalling.Field(marshalling.types.string, 'name', required=True),
            marshalling.List('books', marshalling.Definition('book', 'book'))
        ]


marshalling.register(Person, 'person')
