from enum import unique, Enum, auto


@unique
class Method(Enum):
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()

    @property
    def http_verb(self):
        if self.value == Method.GET.value:
            return 'GET'
        elif self.value == Method.POST.value:
            return 'POST'
        elif self.value == Method.PUT.value:
            return 'PUT'
        elif self.value == Method.PATCH.value:
            return 'PATCH'
        elif self.value == Method.DELETE.value:
            return 'DELETE'
