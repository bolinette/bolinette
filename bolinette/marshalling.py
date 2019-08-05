import json
from functools import wraps

from flask import request, abort, Response

from bolinette import validate, response, mapper

_registered_defs = {}


class MarshallingObject:
    pass


class Field(MarshallingObject):
    def __init__(self, name, **kwargs):
        self.name = name
        self.required = kwargs.get('required', False)
        self.function = kwargs.get('function')
        self.formatting = kwargs.get('formatting')

    def __repr__(self):
        return f'<MarshallingField {self.name}>'


class List(MarshallingObject):
    def __init__(self, element):
        self.element = element

    def __repr__(self):
        return f'<MarshallingList [{repr(self.element)}]>'


class Definition(MarshallingObject):
    def __init__(self, model, name):
        self.fields = []
        self.model = model
        self.name = name
        self.initialized = False
        _registered_defs[name] = self

    def __repr__(self):
        return f'<MarshallingModel {self.name}>'


def register(model, name):
    def create_defs(k, params):
        for key, payload in params:
            dto = Definition(model, f'{name}.{k}.{key}')
            for field in payload:
                dto.fields.append(field)
            dto.initialized = True
    if hasattr(model, 'payloads'):
        create_defs('expects', model.payloads())
    if hasattr(model, 'responses'):
        create_defs('returns', model.responses())


def expects(model, key):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            payload = request.get_json(silent=True) or {}
            name = f'{model}.expects.{key}'
            dto = _registered_defs.get(name)
            if dto is None:
                message, code = response.internal_server_error(
                    f'marshalling.unknown_definition:{model}:{key}')
                abort(Response(json.dumps(message), code, mimetype='application/json'))
            validate.payload(dto, payload)
            kwargs['payload'] = payload
            return func(*args, **kwargs)
        return inner
    return wrapper


def returns(model, key):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            name = f'{model}.returns.{key}'
            dto = _registered_defs.get(name)
            if dto is None:
                message, code = response.internal_server_error(
                    f'marshalling.unknown_definition:{model}:{key}')
                abort(Response(json.dumps(message), code, mimetype='application/json'))
            res, code = func(*args, **kwargs)
            if res.get('data') is not None:
                res['data'] = mapper.marshall(dto, res['data'])
            return res, code
        return inner
    return wrapper
