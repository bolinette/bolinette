from bolinette import db, marshalling

users_roles = db.Table('users_roles',
                       db.Column('u_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
                       db.Column('r_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True))


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)

    roles = db.relationship('Role', secondary=users_roles, lazy='subquery',
                            backref=db.backref('pages', lazy=True))

    @staticmethod
    def payloads():
        yield 'register', [
            marshalling.Field('username', required=True),
            marshalling.Field('email', required=True),
            marshalling.Field('password', required=True)
        ]
        yield 'login', [
            marshalling.Field('username', required=True),
            marshalling.Field('password', required=True)
        ]

    @staticmethod
    def responses():
        yield 'private', [
            marshalling.Field('username', required=True),
            marshalling.Field('email', required=True)
        ]
        yield 'public', [
            marshalling.Field('username', required=True)
        ]

    def __repr__(self):
        return f'<User {self.username}>'


marshalling.register(User, 'user')
