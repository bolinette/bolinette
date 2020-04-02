from bolinette import response, mapping, db
from bolinette.db import TypeClasses
from bolinette.exceptions import EntityNotFoundError, AbortRequestException

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
    name = model.__tablename__.lower()

    def create_defs(collection, params):
        for param in params:
            if isinstance(param, list):
                key = 'default'
                payload = param
            else:
                key, payload = param
            definition = mapping.Definition(name, name, key)
            for field in payload:
                definition.fields.append(field)
            collection[definition.key] = definition

    if hasattr(model, 'payloads'):
        create_defs(_registered_payloads, model.payloads())
    if hasattr(model, 'responses'):
        create_defs(_registered_responses, model.responses())
    if name not in _registered_models:
        _registered_models[name] = model


def marshall(definition, entity, skip_none=False, as_list=False):
    if not entity:
        return None
    if as_list:
        return [marshall(definition, e, skip_none, False) for e in entity]
    data = {}
    for field in definition.fields:
        if isinstance(field, mapping.Field):
            if field.function is not None:
                value = field.function(entity)
            else:
                value = getattr(entity, field.key, None)
            if field.formatting is not None:
                value = field.formatting(value)
            if not skip_none or value is not None:
                data[field.name] = value
        elif isinstance(field, mapping.Definition):
            d = get_response(field.key)
            data[field.name] = marshall(d, getattr(entity, field.name), skip_none, False)
        elif isinstance(field, mapping.List):
            d = get_response(field.element.key)
            data[field.name] = marshall(d, getattr(entity, field.name), skip_none, True)
    return data


def link_foreign_entities(definition, params):
    errors = []
    for field in definition.fields:
        if isinstance(field.type, TypeClasses.ForeignKey):
            value = params.get(field.name, None)
            model = get_model(field.type.model)
            if value is not None and model is not None:
                entity = db.engine.session.query(model).filter_by(**{field.type.key: value}).first()
                if entity is None:
                    errors.append((field.type.model, field.type.key, value))
    if len(errors) > 0:
        raise EntityNotFoundError(params=errors)
