from bolinette import db, mapping


class Person(db.types.Model):
    __tablename__ = 'people'

    id = db.types.Column(db.types.Integer, primary_key=True)
    name = db.types.Column(db.types.String, nullable=False)

    @staticmethod
    def payloads():
        yield [
            mapping.Field(mapping.types.string, 'name', required=True)
        ]

    @staticmethod
    def responses():
        yield [
            mapping.Field(mapping.types.string, 'name', required=True)
        ]
        yield 'complete', [
            mapping.Field(mapping.types.string, 'name', required=True),
            mapping.List('books', mapping.Definition('book', 'book'))
        ]


mapping.register(Person, 'person')
