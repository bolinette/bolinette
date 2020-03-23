from bolinette import db, mapping, env

users_roles = db.types.Table(
    'users_roles',
    db.types.Model.metadata,
    db.types.Column('u_id', db.types.Integer, db.types.ForeignKey('users.id'), primary_key=True),
    db.types.Column('r_id', db.types.Integer, db.types.ForeignKey('roles.id'), primary_key=True))


class User(db.types.Model):
    __tablename__ = 'users'

    id = db.types.Column(db.types.Integer, primary_key=True)
    username = db.types.Column(db.types.String(255), unique=True, nullable=False)
    password = db.types.Column(db.types.String(255), nullable=False)
    email = db.types.Column(db.types.String(255), unique=env.init['USER_EMAIL_REQUIRED'],
                            nullable=(not env.init['USER_EMAIL_REQUIRED']))

    roles = db.types.relationship('Role', secondary=users_roles, lazy='subquery',
                                  backref=db.types.backref('users', lazy=True))

    def has_role(self, role):
        return any(filter(lambda r: r.name == role, self.roles))

    @staticmethod
    def payloads():
        yield 'register', [
            mapping.Field(mapping.types.string, 'username', required=True),
            mapping.Field(mapping.types.email, 'email', required=True),
            mapping.Field(mapping.types.password, 'password', required=True)
        ]
        yield 'admin_register', [
            mapping.Field(mapping.types.string, 'username', required=True),
            mapping.Field(mapping.types.email, 'email', required=True),
            mapping.Field(mapping.types.boolean, 'send_mail', required=True)
        ]
        yield 'login', [
            mapping.Field(mapping.types.string, 'username', required=True),
            mapping.Field(mapping.types.password, 'password', required=True)
        ]

    @staticmethod
    def responses():
        yield [
            mapping.Field(mapping.types.string, 'username')
        ]
        yield 'private', [
            mapping.Field(mapping.types.string, 'username'),
            mapping.Field(mapping.types.email, 'email'),
            mapping.List('roles', mapping.Definition('role', 'role'))
        ]

    def __repr__(self):
        return f'<User {self.username}>'


mapping.register(User, 'user')
