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
