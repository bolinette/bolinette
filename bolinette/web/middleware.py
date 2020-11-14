from bolinette import blnt


class Middleware:
    __blnt__: 'MiddlewareMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        self.context = context
        self.options = {}

    async def handle(self, request, params, next_func):
        return await next_func(request, params)

    def __repr__(self):
        return f'<Middleware {self.__blnt__.name}>'


class MiddlewareMetadata:
    def __init__(self, name: str, priority: int, pre_validation: bool):
        self.name = name
        self.priority = priority
        self.pre_validation = pre_validation
