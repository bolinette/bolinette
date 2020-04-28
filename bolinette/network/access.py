from enum import unique, Enum, auto

from bolinette.network import jwt


@unique
class AccessToken(Enum):
    All = auto()
    Optional = auto()
    Required = auto()
    Fresh = auto()
    Refresh = auto()

    def check(self, request):
        return _functions[self.value](request)


_functions = {
    AccessToken.All.value: lambda _: None,
    AccessToken.Optional.value: lambda request: jwt.verify(request, optional=True),
    AccessToken.Required.value: lambda request: jwt.verify(request),
    AccessToken.Fresh.value: lambda request: jwt.verify(request, fresh=True),
    AccessToken.Refresh.value: lambda request: jwt.verify(request)
}
