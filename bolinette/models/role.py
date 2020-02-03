from bolinette import db, seeder, marshalling


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'

    @staticmethod
    def responses():
        yield [
            marshalling.Field(marshalling.types.string, 'name')
        ]


marshalling.register(Role, 'role')


@seeder
def role_seeder():
    db.session.add(Role(name='root'))
    db.session.add(Role(name='admin'))
