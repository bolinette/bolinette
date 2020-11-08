from enum import unique, Enum, auto


@unique
class AccessToken(Enum):
    All = auto()
    Optional = auto()
    Required = auto()
    Fresh = auto()
    Refresh = auto()

    def check(self, context, request):
        _functions = {
            AccessToken.All.value: lambda _: None,
            AccessToken.Optional.value: lambda req: context.jwt.verify(req, optional=True),
            AccessToken.Required.value: lambda req: context.jwt.verify(req),
            AccessToken.Fresh.value: lambda req: context.jwt.verify(req, fresh=True),
            AccessToken.Refresh.value: lambda req: context.jwt.verify(req)
        }
        return _functions[self.value](request)
