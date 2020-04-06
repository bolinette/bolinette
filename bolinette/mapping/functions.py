from datetime import datetime

from bolinette import db
from bolinette.db import TypeClasses
from bolinette.exceptions import ParamConflictError, ParamMissingError


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
