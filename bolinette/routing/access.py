from enum import unique, Enum, auto

from bolinette import jwt


@unique
class AccessType(Enum):
    All = auto()
    Optional = auto()
    Required = auto()
    Fresh = auto()
    Refresh = auto()

    def check(self, request):
        return _functions[self.value](request)


_functions = {
    AccessType.All.value: lambda _: None,
    AccessType.Optional.value: lambda request: jwt.verify(request, optional=True),
    AccessType.Required.value: lambda request: jwt.verify(request),
    AccessType.Fresh.value: lambda request: jwt.verify(request, fresh=True),
    AccessType.Refresh.value: lambda request: jwt.verify(request)
}
