class APIError(Exception):
    def __init__(self, name, messages):
        super().__init__(name)
        if not isinstance(messages, list):
            messages = [messages]
        self.messages = messages

    def __str__(self):
        return ", ".join(self.messages)


class InternalError(APIError):
    def __init__(self, messages, *, name='InternalError'):
        super().__init__(name, messages)


class NotFoundError(APIError):
    def __init__(self, messages, *, name='NotFoundError'):
        super().__init__(name, messages)


class ConflictError(APIError):
    def __init__(self, messages, *, name='ConflictError'):
        super().__init__(name, messages)


class BadRequestError(APIError):
    def __init__(self, messages, *, name='BadRequestError'):
        super().__init__(name, messages)


class ForbiddenError(APIError):
    def __init__(self, messages, *, name='ForbiddenError'):
        super().__init__(name, messages)


class UnauthorizedError(APIError):
    def __init__(self, messages, *, name='UnauthorizedError'):
        super().__init__(name, messages)


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
