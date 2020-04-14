from bolinette import mapping, env, db


@db.model('users_roles')
class UsersRoles(db.types.Model):
    user_id = db.types.Column(db.types.Integer, reference=db.types.Reference('user', 'id'), primary_key=True)
    role_id = db.types.Column(db.types.Integer, reference=db.types.Reference('role', 'id'), primary_key=True)


@db.model('user')
class User(db.types.Model):
    id = db.types.Column(db.types.Integer, primary_key=True)
    username = db.types.Column(db.types.String, unique=True, nullable=False)
    password = db.types.Column(db.types.Password, nullable=False)
    email = db.types.Column(db.types.Email, unique=env.init['USER_EMAIL_REQUIRED'],
                            nullable=(not env.init['USER_EMAIL_REQUIRED']))

    roles = db.types.Relationship('role', secondary='users_roles', lazy='subquery',
                                  backref=db.types.Backref('users', lazy=True))

    picture_id = db.types.Column(db.types.Integer, reference=db.types.Reference('file', 'id'))
    profile_picture = db.types.Relationship('file', foreign_key=picture_id, lazy=False)

    timezone = db.types.Column(db.types.String)

    @classmethod
    def payloads(cls):
        yield 'register', [
            mapping.Column(cls.username, required=True),
            mapping.Column(cls.email, required=True),
            mapping.Column(cls.password, required=True),
            mapping.Column(cls.timezone)
        ]
        yield 'admin_register', [
            mapping.Column(cls.username, required=True),
            mapping.Column(cls.email, required=True),
            mapping.Field(db.types.Boolean, name='send_mail', required=True)
        ]
        yield 'login', [
            mapping.Column(cls.username, required=True),
            mapping.Column(cls.password, required=True)
        ]

    @classmethod
    def responses(cls):
        default = [
            mapping.Column(cls.username),
            mapping.Reference(cls.profile_picture, 'minimal')
        ]
        yield default
        yield 'private', default + [
            mapping.Column(cls.email),
            mapping.List(mapping.Definition('role'), key='roles'),
            mapping.Column(cls.timezone)
        ]

    def __repr__(self):
        return f'<User {self.username}>'
