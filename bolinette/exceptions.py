from collections.abc import Iterator as _Iterator


class APIError(Exception):
    def __init__(self, message: str, params: list[str] = None):
        super().__init__(type(self).__name__)
        self._message = message
        self._params = params or []

    def __str__(self):
        return ':'.join([self._message] + self._params)

    def __repr__(self):
        return f'<APIError {str(self)}>'

    def __getitem__(self, index: int):
        return self._params[index]

    def __setitem__(self, index: int, value: str):
        self._params = self._params[:index - 1] + [value] + self._params[index+1:]

    @property
    def message(self):
        return self._message


class APIErrors(Exception):
    def __init__(self):
        self.errors = []

    def append(self, error: APIError):
        self.errors.append(error)

    def __bool__(self):
        return len(self.errors) > 0

    def __iter__(self) -> _Iterator[APIError]:
        return iter(self.errors)

    def __str__(self):
        return str(self.errors)

    def __repr__(self):
        return f'<APIErrors [{",".join([repr(err) for err in self.errors])}]>'


class InternalError(APIError):
    pass


class NotFoundError(APIError):
    pass


class ConflictError(APIError):
    pass


class BadRequestError(APIError):
    pass


class UnprocessableEntityError(APIError):
    pass


class ForbiddenError(APIError):
    pass


class UnauthorizedError(APIError):
    pass


class EntityNotFoundError(NotFoundError):
    def __init__(self, model: str, key: str, value: str):
        super().__init__(f'entity.not_found', [model, key, value])


class ParamMissingError(UnprocessableEntityError):
    def __init__(self, key: str):
        super().__init__(f'param.required', [key])


class ParamNonNullableError(UnprocessableEntityError):
    def __init__(self, key: str):
        super().__init__(f'param.non_nullable', [key])


class BadParamFormatError(UnprocessableEntityError):
    def __init__(self, key: str, p_type: str):
        super().__init__(f'param.bad_format', [key, p_type])


class ParamConflictError(ConflictError):
    def __init__(self, key, value):
        super().__init__(f'param.conflict', [key, value])


class InitError(Exception):
    def __init__(self, message: str = None, *, inner: Exception = None):
        self.message = message
        self.inner = inner

    def __str__(self):
        if self.message is None:
            return str(self.inner)
        return self.message
