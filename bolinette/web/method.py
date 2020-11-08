from enum import auto, unique, Enum


@unique
class HttpMethod(Enum):
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()

    @property
    def http_verb(self):
        return self.name
