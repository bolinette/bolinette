from functools import wraps

from flask import request

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
                response.abort(*response.internal_server_error(
                    f'marshalling.unknown_definition:{def_key}'))
            kwargs['payload'] = validate.payload(definition, payload, update)
            link_foreign_entities(definition, payload)
            return func(*args, **kwargs)
        return inner
    return wrapper


def returns(model, key='default', **options):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            as_list = options.get('as_list', False)
            skip_none = options.get('skip_none', False)
            def_key = f'{model}.{key}'
            definition = get_response(def_key)
            if definition is None:
                response.abort(*response.internal_server_error(
                    f'marshalling.unknown_definition:{def_key}'))
            res, code = func(*args, **kwargs)
            if res.get('data') is not None:
                if as_list:
                    res['data'] = [marshall(definition, r, skip_none) for r in res['data']]
                else:
                    res['data'] = marshall(definition, res['data'], skip_none)
            return res, code
        return inner
    return wrapper
