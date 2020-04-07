from datetime import datetime

from bolinette import db, mapping
from bolinette.db import TypeClasses
from bolinette.exceptions import ParamConflictError, ParamMissingError, EntityNotFoundError


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
            d = mapping.get_response(field.model_key)
            if field.function and callable(field.function):
                attr = field.function(entity)
            else:
                attr = getattr(entity, field.name)
            data[field.name] = marshall(d, attr, skip_none, False)
        elif isinstance(field, mapping.List):
            d = mapping.get_response(field.element.model_key)
            data[field.name] = marshall(d, getattr(entity, field.name), skip_none, True)
    return data


def link_foreign_entities(definition, params):
    errors = []
    for field in definition.fields:
        if isinstance(field.type, TypeClasses.ForeignKey):
            value = params.get(field.name, None)
            model = mapping.get_model(field.type.model)
            if value is not None and model is not None:
                entity = db.engine.session.query(model).filter_by(**{field.type.key: value}).first()
                if entity is None:
                    errors.append((field.type.model, field.type.key, value))
    if len(errors) > 0:
        raise EntityNotFoundError(params=errors)


def validate_model(model, params, **kwargs):
    excluding = kwargs.get('excluding', [])
    errors = []
    for column in model.__table__.columns:
        key = column.key
        if column.primary_key or key in excluding:
            continue
        value = params.get(key, None)
        if column.unique and value is not None:
            criteria = getattr(model, key) == value
            if db.engine.session.query(model).filter(criteria).first() is not None:
                errors.append((key, value))
    if len(errors) > 0:
        raise ParamConflictError(params=errors)
    return params


def validate_payload(definition, params, patch=False):
    errors = []
    valid = {}
    for field in definition.fields:
        if patch and field.name not in params:
            continue
        value = params.get(field.name, None)
        if value and field.type.of_type(TypeClasses.Date):
            value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        if not value or not len(str(value)):
            if field.required:
                errors.append(field.name)
            else:
                value = field.default
        valid[field.name] = value
    if len(errors) > 0:
        raise ParamMissingError(params=errors)
    return valid


def map_model(model, entity, params, patch=False):
    errors = []
    for column in model.__table__.columns:
        key = column.key
        if column.primary_key or (key not in params and patch):
            continue
        original = getattr(entity, key)
        new = params.get(key, None)
        if original == new:
            continue
        if column.unique and new is not None:
            if db.engine.session.query(model).filter(getattr(model, key) == new).first() is not None:
                errors.append((key, new))
        setattr(entity, key, new)
    if len(errors) > 0:
        raise ParamConflictError(params=errors)
