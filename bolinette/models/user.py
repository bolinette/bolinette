from bolinette import mapping, env, db
from bolinette.models import Role

users_roles = db.defs.table(
    'users_roles',
    db.defs.model.metadata,
    db.defs.column(db.types.integer, db.types.foreign_key('user', 'id'), name='u_id', primary_key=True),
    db.defs.column(db.types.integer, db.types.foreign_key('role', 'id'), name='r_id', primary_key=True))


class User(db.defs.model):
    __tablename__ = 'user'

    id = db.defs.column(db.types.integer, primary_key=True)
    username = db.defs.column(db.types.string, unique=True, nullable=False)
    password = db.defs.column(db.types.string, nullable=False)
    email = db.defs.column(db.types.string, unique=env.init['USER_EMAIL_REQUIRED'],
                           nullable=(not env.init['USER_EMAIL_REQUIRED']))

    roles = db.defs.relationship(Role, secondary=users_roles, lazy='subquery',
                                 backref=db.defs.backref('user', lazy=True))

    def has_role(self, role):
        return any(filter(lambda r: r.name == role, self.roles))

    @staticmethod
    def payloads():
        yield 'register', [
            mapping.Field(db.types.string, key='username', required=True),
            mapping.Field(db.types.email, key='email', required=True),
            mapping.Field(db.types.password, key='password', required=True)
        ]
        yield 'admin_register', [
            mapping.Field(db.types.string, key='username', required=True),
            mapping.Field(db.types.email, key='email', required=True),
            mapping.Field(db.types.boolean, key='send_mail', required=True)
        ]
        yield 'login', [
            mapping.Field(db.types.string, key='username', required=True),
            mapping.Field(db.types.password, key='password', required=True)
        ]

    @staticmethod
    def responses():
        yield [
            mapping.Field(db.types.string, key='username')
        ]
        yield 'private', [
            mapping.Field(db.types.string, key='username'),
            mapping.Field(db.types.email, key='email'),
            mapping.List('roles', mapping.Definition('role', 'role'))
        ]

    def __repr__(self):
        return f'<User {self.username}>'


mapping.register(User)
