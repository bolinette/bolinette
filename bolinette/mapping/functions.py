from datetime import datetime
from typing import Type

from bolinette import db, mapping
from bolinette.exceptions import ParamConflictError, ParamMissingError, EntityNotFoundError


def marshall(definition, entity, *, skip_none=False, as_list=False, use_foreign_key=False):
    if not entity:
        return None
    if as_list:
        return [marshall(definition, e, skip_none=skip_none, as_list=False, use_foreign_key=use_foreign_key)
                for e in entity]
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
        elif isinstance(field, mapping.Reference) and use_foreign_key:
            data[field.foreign_key] = getattr(entity, field.foreign_key)
        elif isinstance(field, mapping.Definition):
            d = mapping.get_response(field.model_name, field.model_key)
            attr = None
            if field.function and callable(field.function):
                attr = field.function(entity)
            elif hasattr(entity, field.name):
                attr = getattr(entity, field.name)
            data[field.name] = marshall(d, attr, skip_none=skip_none, as_list=False, use_foreign_key=use_foreign_key)
        elif isinstance(field, mapping.List):
            d = mapping.get_response(field.element.model_name, field.element.model_key)
            data[field.name] = marshall(d, getattr(entity, field.name), skip_none=skip_none,
                                        as_list=True, use_foreign_key=use_foreign_key)
    return data


def link_foreign_entities(definition, params):
    errors = []
    for field in definition.fields:
        if isinstance(field, mapping.Reference):
            value = params.get(field.foreign_key, None)
            model = db.models.get(field.reference_model)
            if value is not None and model is not None:
                entity = model.query().filter_by(**{field.reference_key: value}).first()
                if entity is None:
                    errors.append((field.reference_model, field.reference_key, value))
    if len(errors) > 0:
        raise EntityNotFoundError(params=errors)


def validate_model(model: Type['db.defs.Model'], params: dict):
    errors = []
    for column in model.get_columns().values():
        key = column.name
        if column.primary_key:
            continue
        value = params.get(key, None)
        if column.unique and value is not None:
            if model.query().filter(column == value).first() is not None:
                errors.append((key, value))
    if len(errors) > 0:
        raise ParamConflictError(params=errors)
    return params


def validate_payload(definition, params, patch=False):
    errors = []
    valid = {}
    for field in definition.fields:
        if isinstance(field, mapping.Reference):
            if patch and field.foreign_key not in params:
                continue
            link = params.get(field.foreign_key)
            if not link or not len(str(link)):
                if field.required:
                    errors.append(field.foreign_key)
                else:
                    link = field.default
            valid[field.foreign_key] = link
        if isinstance(field, mapping.Field):
            if patch and field.name not in params:
                continue
            value = params.get(field.name, None)
            if value and field.type == db.types.Date:
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


def map_model(model: Type['db.defs.Model'], entity, params, patch=False):
    errors = []
    for _, column in model.get_columns().items():
        key = column.name
        if column.primary_key or (key not in params and patch):
            continue
        original = getattr(entity, key)
        new = params.get(key, None)
        if original == new:
            continue
        if column.unique and new is not None:
            if model.query().filter(getattr(model, key) == new).first() is not None:
                errors.append((key, new))
        setattr(entity, key, new)
    if len(errors) > 0:
        raise ParamConflictError(params=errors)
