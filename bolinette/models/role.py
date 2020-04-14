from bolinette import mapping, db


@db.model('role')
class Role(db.types.Model):
    id = db.types.Column(db.types.Integer, primary_key=True)
    name = db.types.Column(db.types.String, unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'

    @classmethod
    def payloads(cls):
        yield [
            mapping.Column(cls.name, required=True)
        ]

    @classmethod
    def responses(cls):
        yield [
            mapping.Column(cls.name)
        ]
        yield 'complete', [
            mapping.Column(cls.name),
            mapping.List(mapping.Definition('user'), key='users')
        ]
