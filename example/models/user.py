from bolinette import types
from bolinette.data import model, mapping
from bolinette.data.defaults.models import UserModel


class UserWithFirstName:
    first_name = types.defs.Column(types.db.String, nullable=False)


@model('user', definitions='append')
class UserModelExtended(UserModel, UserWithFirstName):
    last_name = types.defs.Column(types.db.String, nullable=False)

    def payloads(self):
        extends = [
            mapping.Column(self.first_name, required=True),
            mapping.Column(self.last_name, required=True)
        ]
        yield 'register', extends
        yield 'admin_register', extends
