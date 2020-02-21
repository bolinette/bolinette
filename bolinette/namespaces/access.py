from enum import Enum, unique, auto

from flask_jwt_extended import (
    verify_jwt_in_request, verify_jwt_in_request_optional, verify_fresh_jwt_in_request,
    verify_jwt_refresh_token_in_request, current_user
)

from bolinette import response


@unique
class AccessToken(Enum):
    All = auto()
    Optional = auto()
    Required = auto()
    Fresh = auto()
    Refresh = auto()

    def check_roles(self, roles):
        user_roles = set(map(lambda r: r.name, current_user.roles))
        if 'root' not in user_roles and not len(user_roles.intersection(set(roles))):
            response.abort(*response.forbidden(f'user.forbidden:{",".join(roles)}'))

    def check(self, roles):
        _functions[self.value]()
        if len(roles):
            self.check_roles(roles)


_functions = {
    AccessToken.All.value: lambda: None,
    AccessToken.Optional.value: verify_jwt_in_request_optional,
    AccessToken.Required.value: verify_jwt_in_request,
    AccessToken.Fresh.value: verify_fresh_jwt_in_request,
    AccessToken.Refresh.value: verify_jwt_refresh_token_in_request
}
