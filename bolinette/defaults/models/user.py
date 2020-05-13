from bolinette import mapping, env, types, data
from bolinette.decorators import model


@model('users_roles')
class UsersRoles(data.Model):
    user_id = types.Column(types.Integer, reference=types.Reference('user', 'id'), primary_key=True)
    role_id = types.Column(types.Integer, reference=types.Reference('role', 'id'), primary_key=True)


@model('user')
class User(data.Model):
    id = types.Column(types.Integer, primary_key=True)
    username = types.Column(types.String, unique=True, nullable=False)
    password = types.Column(types.Password, nullable=False)
    email = types.Column(types.Email, unique=env.init['USER_EMAIL_REQUIRED'],
                              nullable=(not env.init['USER_EMAIL_REQUIRED']))

    roles = types.Relationship('role', secondary='users_roles', lazy='subquery',
                                    backref=types.Backref('users', lazy=True))

    picture_id = types.Column(types.Integer, reference=types.Reference('file', 'id'))
    profile_picture = types.Relationship('file', foreign_key=picture_id, lazy=False)

    timezone = types.Column(types.String)

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
            mapping.Field(types.Boolean, name='send_mail', required=True)
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
