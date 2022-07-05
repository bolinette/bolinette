from collections.abc import Iterator as _Iterator


class BolinetteError(Exception):
    def __init__(self, message: str, params: list[str] = None):
        super().__init__(type(self).__name__)
        self._message = message
        self._params = params or []

    def __str__(self):
        return ":".join([self._message] + self._params)

    def __repr__(self):
        return f"<APIError {str(self)}>"

    def __getitem__(self, index: int):
        return self._params[index]

    def __setitem__(self, index: int, value: str):
        self._params = self._params[: index - 1] + [value] + self._params[index + 1 :]

    @property
    def message(self):
        return self._message


class ErrorCollection(Exception):
    def __init__(self):
        self.errors = []

    def append(self, error: BolinetteError):
        self.errors.append(error)

    def __bool__(self):
        return len(self.errors) > 0

    def __iter__(self) -> _Iterator[BolinetteError]:
        return iter(self.errors)

    def __str__(self):
        return str(self.errors)

    def __repr__(self):
        return f'<APIErrors [{",".join([repr(err) for err in self.errors])}]>'


class InternalError(BolinetteError):
    pass


class NotFoundError(BolinetteError):
    pass


class ConflictError(BolinetteError):
    pass


class BadRequestError(BolinetteError):
    pass


class UnprocessableEntityError(BolinetteError):
    pass


class ForbiddenError(BolinetteError):
    pass


class UnauthorizedError(BolinetteError):
    pass


class EntityNotFoundError(NotFoundError):
    def __init__(self, model: str, key: str, value: str):
        super().__init__("entity.not_found", [model, key, value])


class ParamMissingError(UnprocessableEntityError):
    def __init__(self, key: str):
        super().__init__("param.required", [key])


class ParamNonNullableError(UnprocessableEntityError):
    def __init__(self, key: str):
        super().__init__("param.non_nullable", [key])


class BadParamFormatError(UnprocessableEntityError):
    def __init__(self, key: str, p_type: str):
        super().__init__("param.bad_format", [key, p_type])


class ParamConflictError(ConflictError):
    def __init__(self, key, value):
        super().__init__("param.conflict", [key, value])


class InitError(Exception):
    def __init__(self, message: str = None, *, inner: Exception = None):
        self.message = message
        self.inner = inner

    def __str__(self):
        if self.message is None:
            return str(self.inner)
        return self.message
