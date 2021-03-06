from bolinette import types, mapping
from bolinette.decorators import model
from bolinette.defaults.models import User


class UserWithFirstName:
    first_name = types.defs.Column(types.db.String, nullable=False)


@model('user', definitions='append')
class UserExtended(User, UserWithFirstName):
    last_name = types.defs.Column(types.db.String, nullable=False)

    def payloads(self):
        extends = [
            mapping.Column(self.first_name, required=True),
            mapping.Column(self.last_name, required=True)
        ]
        yield 'register', extends
        yield 'admin_register', extends
