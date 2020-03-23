from bolinette import db, mapping


class Role(db.types.Model):
    __tablename__ = 'roles'

    id = db.types.Column(db.types.Integer, primary_key=True)
    name = db.types.Column(db.types.String(255), unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'

    @staticmethod
    def payloads():
        yield [
            mapping.Field(mapping.types.string, 'name')
        ]

    @staticmethod
    def responses():
        yield [
            mapping.Field(mapping.types.string, 'name')
        ]
        yield 'complete', [
            mapping.Field(mapping.types.string, 'name'),
            mapping.List('users', mapping.Definition('user', 'user'))
        ]


mapping.register(Role, 'role')
