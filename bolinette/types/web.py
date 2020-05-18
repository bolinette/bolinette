from enum import unique, Enum, auto


@unique
class HttpMethod(Enum):
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()

    @property
    def http_verb(self):
        if self.value == HttpMethod.GET.value:
            return 'GET'
        elif self.value == HttpMethod.POST.value:
            return 'POST'
        elif self.value == HttpMethod.PUT.value:
            return 'PUT'
        elif self.value == HttpMethod.PATCH.value:
            return 'PATCH'
        elif self.value == HttpMethod.DELETE.value:
            return 'DELETE'


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
