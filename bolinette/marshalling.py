import json
from functools import wraps

from flask import request, abort, Response

from bolinette import validate, response

_registered_responses = {}
_registered_payloads = {}


def get_def(collection, key):
    d = collection.get(key)
    if d is None:
        message, code = response.internal_server_error(
            f'marshalling.unknown_definition:{key}')
        abort(Response(json.dumps(message), code, mimetype='application/json'))
    return d


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
    def __init__(self, name, key):
        self.fields = []
        self.name = name
        self.key = key
        self.initialized = False

    def __repr__(self):
        return f'<MarshallingModel {self.name}>'


def register(model, name):
    def create_defs(collection, params):
        for key, payload in params:
            definition = Definition(name, f'{name}.{key}')
            for field in payload:
                definition.fields.append(field)
            definition.initialized = True
            collection[definition.key] = definition
    if hasattr(model, 'payloads'):
        create_defs(_registered_payloads, model.payloads())
    if hasattr(model, 'responses'):
        create_defs(_registered_responses, model.responses())


def marshall(definition, entity):
    data = {}
    for field in definition.fields:
        if isinstance(field, Field):
            if field.function is not None:
                value = field.function(entity)
            else:
                value = getattr(entity, field.name, None)
            if field.formatting is not None:
                value = field.formatting(value)
            data[field.name] = value
        elif isinstance(field, Definition):
            if not field.initialized:
                d = get_def(_registered_responses, field.key)
                field.initialized = True
                field.fields = d.fields
            data[field.name] = marshall(field, getattr(entity, field.name))
    return data


def expects(model, key='default'):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            payload = request.get_json(silent=True) or {}
            def_key = f'{model}.{key}'
            definition = get_def(_registered_payloads, def_key)
            if definition is None:
                message, code = response.internal_server_error(
                    f'marshalling.unknown_definition:{def_key}')
                abort(Response(json.dumps(message), code, mimetype='application/json'))
            validate.payload(definition, payload)
            kwargs['payload'] = payload
            return func(*args, **kwargs)
        return inner
    return wrapper


def returns(model, key='default'):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            def_key = f'{model}.{key}'
            definition = get_def(_registered_responses, def_key)
            if definition is None:
                message, code = response.internal_server_error(
                    f'marshalling.unknown_definition:{def_key}')
                abort(Response(json.dumps(message), code, mimetype='application/json'))
            res, code = func(*args, **kwargs)
            if res.get('data') is not None:
                res['data'] = marshall(definition, res['data'])
            return res, code
        return inner
    return wrapper
