from bolinette import types, core, blnt, mapping
from bolinette.decorators import model


@model('users_roles')
class UsersRoles(core.Model):
    user_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('user', 'id'), primary_key=True)
    role_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('role', 'id'), primary_key=True)


@model('user')
class User(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    username = types.defs.Column(types.db.String, unique=True, nullable=False)
    password = types.defs.Column(types.db.Password, nullable=False)
    email = types.defs.Column(types.db.Email, unique=blnt.init['user_email_required'],
                              nullable=(not blnt.init['user_email_required']))

    roles = types.defs.Relationship('role', secondary='users_roles', lazy='subquery',
                                    backref=types.defs.Backref('users', lazy=True))

    picture_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('file', 'id'))
    profile_picture = types.defs.Relationship('file', foreign_key=picture_id, lazy=False)

    timezone = types.defs.Column(types.db.String)

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
            mapping.Field(types.db.Boolean, name='send_mail', required=True)
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
