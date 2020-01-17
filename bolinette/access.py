from enum import Enum, unique, auto

import flask_jwt_extended


@unique
class AccessToken(Enum):
    All = auto()
    Optional = auto()
    Required = auto()
    Fresh = auto()
    Refresh = auto()

    def check(self):
        _functions[self.value]()


_functions = {
    AccessToken.All.value: lambda: None,
    AccessToken.Optional.value: flask_jwt_extended.verify_jwt_in_request_optional,
    AccessToken.Required.value: flask_jwt_extended.verify_jwt_in_request,
    AccessToken.Fresh.value: flask_jwt_extended.verify_fresh_jwt_in_request,
    AccessToken.Refresh.value: flask_jwt_extended.verify_jwt_refresh_token_in_request
}
