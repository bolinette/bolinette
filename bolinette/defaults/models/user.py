from bolinette import env, types, blnt
from bolinette.decorators import model


@model('users_roles')
class UsersRoles(blnt.Model):
    user_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('user', 'id'), primary_key=True)
    role_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('role', 'id'), primary_key=True)


@model('user')
class User(blnt.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    username = types.defs.Column(types.db.String, unique=True, nullable=False)
    password = types.defs.Column(types.db.Password, nullable=False)
    email = types.defs.Column(types.db.Email, unique=env.init['USER_EMAIL_REQUIRED'],
                              nullable=(not env.init['USER_EMAIL_REQUIRED']))

    roles = types.defs.Relationship('role', secondary='users_roles', lazy='subquery',
                                    backref=types.defs.Backref('users', lazy=True))

    picture_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('file', 'id'))
    profile_picture = types.defs.Relationship('file', foreign_key=picture_id, lazy=False)

    timezone = types.defs.Column(types.db.String)

    @classmethod
    def payloads(cls):
        yield 'register', [
            types.mapping.Column(cls.username, required=True),
            types.mapping.Column(cls.email, required=True),
            types.mapping.Column(cls.password, required=True),
            types.mapping.Column(cls.timezone)
        ]
        yield 'admin_register', [
            types.mapping.Column(cls.username, required=True),
            types.mapping.Column(cls.email, required=True),
            types.mapping.Field(types.db.Boolean, name='send_mail', required=True)
        ]
        yield 'login', [
            types.mapping.Column(cls.username, required=True),
            types.mapping.Column(cls.password, required=True)
        ]

    @classmethod
    def responses(cls):
        default = [
            types.mapping.Column(cls.username),
            types.mapping.Reference(cls.profile_picture, 'minimal')
        ]
        yield default
        yield 'private', default + [
            types.mapping.Column(cls.email),
            types.mapping.List(types.mapping.Definition('role'), key='roles'),
            types.mapping.Column(cls.timezone)
        ]
