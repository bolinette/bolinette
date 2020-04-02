from bolinette import mapping, db


class File(db.defs.model):
    __tablename__ = 'file'

    id = db.defs.column(db.types.integer, primary_key=True)
    key = db.defs.column(db.types.string, nullable=False)
    name = db.defs.column(db.types.string, nullable=False)
    mime = db.defs.column(db.types.string, nullable=False)

    @staticmethod
    def responses():
        yield [
            mapping.Field(db.types.string, key='key'),
            mapping.Field(db.types.string, key='name'),
            mapping.Field(db.types.string, key='mime')
        ]
        yield 'minimal', [
            mapping.Field(db.types.string, key='key')
        ]


mapping.register(File)
