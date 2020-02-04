from enum import Enum, unique, auto

import flask_jwt_extended

from bolinette import response


@unique
class AccessToken(Enum):
    All = auto()
    Optional = auto()
    Required = auto()
    Fresh = auto()
    Refresh = auto()

    def check_roles(self, roles):
        user_roles = set(map(lambda r: r.name, flask_jwt_extended.current_user.roles))
        if 'root' not in user_roles and not len(user_roles.intersection(set(roles))):
            response.abort(*response.forbidden(f'user.forbidden:{",".join(roles)}'))

    def check(self, roles):
        _functions[self.value]()
        if len(roles):
            self.check_roles(roles)


_functions = {
    AccessToken.All.value: lambda: None,
    AccessToken.Optional.value: flask_jwt_extended.verify_jwt_in_request_optional,
    AccessToken.Required.value: flask_jwt_extended.verify_jwt_in_request,
    AccessToken.Fresh.value: flask_jwt_extended.verify_fresh_jwt_in_request,
    AccessToken.Refresh.value: flask_jwt_extended.verify_jwt_refresh_token_in_request
}
