class APIError(Exception):
    def __init__(self, message, *, name="APIError"):
        super().__init__(name)
        self.message = message

    def __str__(self):
        return self.message

    def __repr__(self):
        return f'<APIError {self.message}>'


class APIErrors(Exception):
    def __init__(self):
        self.errors = []

    def append(self, error: APIError):
        self.errors.append(error)

    def __bool__(self):
        return len(self.errors) > 0

    def __repr__(self):
        return f'<APIErrors [{",".join([repr(err) for err in self.errors])}]>'


class InternalError(APIError):
    def __init__(self, message, *, name='InternalError'):
        super().__init__(message, name=name)


class NotFoundError(APIError):
    def __init__(self, message, *, name='NotFoundError'):
        super().__init__(message, name=name)


class ConflictError(APIError):
    def __init__(self, message, *, name='ConflictError'):
        super().__init__(message, name=name)


class BadRequestError(APIError):
    def __init__(self, message, *, name='BadRequestError'):
        super().__init__(message, name=name)


class ForbiddenError(APIError):
    def __init__(self, message, *, name='ForbiddenError'):
        super().__init__(message, name=name)


class UnauthorizedError(APIError):
    def __init__(self, message, *, name='UnauthorizedError'):
        super().__init__(message, name=name)


class EntityNotFoundError(NotFoundError):
    def __init__(self, model, key, value):
        super().__init__(f'entity.not_found:{model}:{key}:{value}', name='EntityNotFoundError')


class ParamMissingError(BadRequestError):
    def __init__(self, key):
        super().__init__(f'param.required:{key}', name='ParamMissingError')


class ParamNonNullableError(BadRequestError):
    def __init__(self, key):
        super().__init__(f'param.non_nullable:{key}', name='ParamMissingError')


class ParamConflictError(ConflictError):
    def __init__(self, key, value):
        super().__init__(f'param.conflict:{key}:{value}', name='ParamConflictError')


class InitError(Exception):
    def __init__(self, message: str = None, *, inner: Exception = None):
        self.message = message
        self.inner = inner

    def __str__(self):
        if self.message is None:
            return str(self.inner)
        return self.message
