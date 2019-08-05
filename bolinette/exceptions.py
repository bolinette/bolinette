from enum import Enum


class ErrorType(Enum):
    NOT_FOUND = 0
    CONFLICT = 1
    BAD_REQUEST = 2


class APIError(Exception):
    Type = ErrorType

    def __init__(self, message, e_type):
        super().__init__(message)
        self.type = e_type


class EntityNotFoundError(APIError):
    def __init__(self, **kwargs):
        super().__init__('EntityNotFoundError', ErrorType.NOT_FOUND)
        params = kwargs.get('params', None)
        model = kwargs.get('model', None)
        key = kwargs.get('key', None)
        value = kwargs.get('value', None)
        if params is None:
            params = [(model, key, value)]
        self.messages = [f'{m}.not_found:{k}:{v}' for m, k, v in params]


class ParamMissingError(APIError):
    def __init__(self, **kwargs):
        super().__init__('ParamMissingError', ErrorType.BAD_REQUEST)
        params = kwargs.get('params', None)
        key = kwargs.get('key', None)
        if params is None:
            params = [key]
        self.messages = [f'param.required:{k}' for k in params]


class ParamConflictError(APIError):
    def __init__(self, **kwargs):
        super().__init__('ParamConflictError', ErrorType.CONFLICT)
        params = kwargs.get('params', None)
        key = kwargs.get('key', None)
        value = kwargs.get('value', None)
        if params is None:
            params = [(key, value)]
        self.messages = [f'param.conflict:{k}:{v}' for k, v in params]
