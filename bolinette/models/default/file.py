from bolinette import mapping, db


@db.model('file')
class File(db.defs.Model):
    id = db.defs.Column(db.types.Integer, primary_key=True)
    key = db.defs.Column(db.types.String, nullable=False)
    name = db.defs.Column(db.types.String, nullable=False)
    mime = db.defs.Column(db.types.String, nullable=False)

    @classmethod
    def responses(cls):
        yield [
            mapping.Column(cls.key),
            mapping.Column(cls.name),
            mapping.Column(cls.mime)
        ]
        yield 'minimal', [
            mapping.Column(cls.key)
        ]
