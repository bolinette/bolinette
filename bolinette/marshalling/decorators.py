import json
from functools import wraps

from flask import request, abort, Response

from bolinette import response, validate
from bolinette.marshalling import get_payload, get_response, marshall
from bolinette.marshalling.definitions import link_foreign_entities


def expects(model, key='default', update=False):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            payload = request.get_json(silent=True) or {}
            def_key = f'{model}.{key}'
            definition = get_payload(def_key)
            if definition is None:
                message, code = response.internal_server_error(
                    f'marshalling.unknown_definition:{def_key}')
                abort(Response(json.dumps(message), code, mimetype='application/json'))
            kwargs['payload'] = validate.payload(definition, payload, update)
            link_foreign_entities(definition, payload)
            return func(*args, **kwargs)
        return inner
    return wrapper


def returns(model, key='default', as_list=False):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            def_key = f'{model}.{key}'
            definition = get_response(def_key)
            if definition is None:
                message, code = response.internal_server_error(
                    f'marshalling.unknown_definition:{def_key}')
                abort(Response(json.dumps(message), code, mimetype='application/json'))
            res, code = func(*args, **kwargs)
            if res.get('data') is not None:
                if as_list:
                    res['data'] = [marshall(definition, r) for r in res['data']]
                else:
                    res['data'] = marshall(definition, res['data'])
            return res, code
        return inner
    return wrapper
