from bolinette import response, mapping
from bolinette.exceptions import AbortRequestException

_registered_models = {}
_registered_responses = {}
_registered_payloads = {}


def _get_def(collection, key):
    d = collection.get(key)
    if d is None:
        raise AbortRequestException(response.internal_server_error(f'mapping.unknown_definition:{key}'))
    return d


def get_response(key):
    return _get_def(_registered_responses, key)


def get_payload(key):
    return _get_def(_registered_payloads, key)


def get_model(name):
    return _registered_models.get(name)


def register(model):
    model_name = model.__tablename__.lower()

    def create_defs(collection, params):
        for param in params:
            if isinstance(param, list):
                model_key = 'default'
                payload = param
            else:
                model_key, payload = param
            definition = mapping.Definition(model_name, model_key)
            for field in payload:
                definition.fields.append(field)
            collection[definition.model_key] = definition

    if hasattr(model, 'payloads'):
        create_defs(_registered_payloads, model.payloads())
    if hasattr(model, 'responses'):
        create_defs(_registered_responses, model.responses())
    if model_name not in _registered_models:
        _registered_models[model_name] = model
