from bolinette import mapping, db


class Role(db.defs.model):
    __tablename__ = 'role'

    id = db.defs.column(db.types.integer, primary_key=True)
    name = db.defs.column(db.types.string, unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'

    @staticmethod
    def payloads():
        yield [
            mapping.Field(db.types.string, key='name', required=True)
        ]

    @staticmethod
    def responses():
        yield [
            mapping.Field(db.types.string, key='name')
        ]
        yield 'complete', [
            mapping.Field(db.types.string, key='name'),
            mapping.List('users', mapping.Definition('user', 'user'))
        ]


mapping.register(Role)
