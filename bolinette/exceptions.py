from bolinette import response


class APIError(Exception):
    def __init__(self, name, function, messages):
        super().__init__(name)
        self.function = function
        self.messages = messages

    def __str__(self):
        return ", ".join(self.messages)

    @property
    def response(self):
        return self.function(self.messages)


class NotFoundError(APIError):
    def __init__(self, messages, *, name=None):
        super().__init__(name or type(self).__name__,
                         response.not_found, messages)


class ConflictError(APIError):
    def __init__(self, messages, *, name=None):
        super().__init__(name or type(self).__name__,
                         response.conflict, messages)


class BadRequestError(APIError):
    def __init__(self, messages, *, name=None):
        super().__init__(name or type(self).__name__,
                         response.bad_request, messages)


class ForbiddenError(APIError):
    def __init__(self, messages, *, name=None):
        super().__init__(name or type(self).__name__,
                         response.forbidden, messages)


class UnauthorizedError(APIError):
    def __init__(self, messages, *, name=None):
        super().__init__(name or type(self).__name__,
                         response.unauthorized, messages)


class EntityNotFoundError(NotFoundError):
    def __init__(self, **kwargs):
        params = kwargs.get('params', None)
        model = kwargs.get('model', None)
        key = kwargs.get('key', None)
        value = kwargs.get('value', None)
        if params is None:
            params = [(model, key, value)]
        messages = [f'{m}.not_found:{k}:{v}' for m, k, v in params]
        super().__init__(messages, name='EntityNotFoundError')


class ParamMissingError(BadRequestError):
    def __init__(self, **kwargs):
        params = kwargs.get('params', None)
        key = kwargs.get('key', None)
        if params is None:
            params = [key]
        messages = [f'param.required:{k}' for k in params]
        super().__init__(messages, name='ParamMissingError')


class ParamConflictError(ConflictError):
    def __init__(self, **kwargs):
        params = kwargs.get('params', None)
        key = kwargs.get('key', None)
        value = kwargs.get('value', None)
        if params is None:
            params = [(key, value)]
        messages = [f'param.conflict:{k}:{v}' for k, v in params]
        super().__init__(messages, name='ParamConflictError')


class AbortRequestException(Exception):
    def __init__(self, resp):
        self.response = resp
