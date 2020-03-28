from bolinette import mapping, db


class Person(db.defs.model):
    __tablename__ = 'person'

    id = db.defs.column(db.types.integer, primary_key=True)
    first_name = db.defs.column(db.types.string, nullable=False)
    last_name = db.defs.column(db.types.string, nullable=False)

    @staticmethod
    def payloads():
        yield [
            mapping.Field(db.types.string, key='first_name', required=True),
            mapping.Field(db.types.string, key='last_name', required=True)
        ]

    @staticmethod
    def responses():
        yield [
            mapping.Field(db.types.string, key='first_name'),
            mapping.Field(db.types.string, key='last_name'),
            mapping.Field(db.types.string, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}')
        ]
        yield 'complete', [
            mapping.Field(db.types.string, key='first_name'),
            mapping.Field(db.types.string, key='last_name'),
            mapping.Field(db.types.string, name='full_name', function=lambda p: f'{p.first_name} {p.last_name}'),
            mapping.List('books', mapping.Definition('book', 'book'))
        ]


mapping.register(Person)
