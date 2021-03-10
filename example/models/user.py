from bolinette import types, mapping
from bolinette.decorators import model
from bolinette.defaults.models import User


class UserWithFirstName:
    first_name = types.defs.Column(types.db.String, nullable=False)


@model('user')
class UserExtended(User, UserWithFirstName):
    last_name = types.defs.Column(types.db.String, nullable=False)

    def payloads(self):
        payloads = super().payloads()
        for payload in payloads:
            if len(payload) == 2 and payload[0] in ['register', 'admin_register']:
                payload[1].append(mapping.Column(self.first_name, required=True))
                payload[1].append(mapping.Column(self.last_name, required=True))
            yield payload
