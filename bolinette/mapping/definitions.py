from typing import Type

from bolinette import response, mapping, db
from bolinette.exceptions import AbortRequestException

_registered_responses = {}
_registered_payloads = {}


def _get_def(collection, model_name, key):
    m = collection.get(model_name)
    if m is None:
        raise AbortRequestException(response.internal_server_error(f'mapping.unknown_model:{model_name}'))
    d = m.get(key)
    if d is None:
        raise AbortRequestException(response.internal_server_error(f'mapping.unknown_definition:{key}'))
    return d


def get_response(model_name: str, key: str):
    return _get_def(_registered_responses, model_name, key)


def get_payload(model_name: str, key: str):
    return _get_def(_registered_payloads, model_name, key)


def register(model_name: str, model: Type['db.defs.Model']):
    def create_defs(collection, params):
        if params is None:
            return
        for param in params:
            if isinstance(param, list):
                model_key = 'default'
                payload = param
            else:
                model_key, payload = param
            definition = mapping.Definition(model_name, model_key)
            for field in payload:
                definition.fields.append(field)
            if definition.model_name not in collection:
                collection[definition.model_name] = {}
            collection[definition.model_name][definition.model_key] = definition

    create_defs(_registered_payloads, model.payloads())
    create_defs(_registered_responses, model.responses())
