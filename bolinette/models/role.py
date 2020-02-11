from bolinette import db, marshalling


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'

    @staticmethod
    def payloads():
        yield [
            marshalling.Field(marshalling.types.string, 'name')
        ]

    @staticmethod
    def responses():
        yield [
            marshalling.Field(marshalling.types.string, 'name')
        ]
        yield 'complete', [
            marshalling.Field(marshalling.types.string, 'name'),
            marshalling.List('users', marshalling.Definition('user', 'user'))
        ]


marshalling.register(Role, 'role')
