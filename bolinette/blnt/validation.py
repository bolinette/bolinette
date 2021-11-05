from typing import Any

from dateutil import parser as date_parser

from bolinette import abc, blnt, core, types, exceptions, mapping
from bolinette.exceptions import APIErrors, APIError
from bolinette.utils.functions import is_db_entity


class Validator(abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)

    async def validate_payload(self, model: str, key: str, values, patch=False, attr_prefix: str = None):
        if attr_prefix is None:
            attr_prefix = ''
        api_errors = APIErrors()
        valid = {}
        definition = self.context.mapper.payload(model, key)
        for field in definition.fields:
            field_key = field.key
            field_name = field.name
            if patch and field_name not in values:
                continue
            if isinstance(field, mapping.Reference):
                try:
                    valid[field_name] = await self._validate_linked_entity(field, field_name, values,
                                                                           f'{attr_prefix}{field_name}.')
                    if is_db_entity(valid[field_name]):
                        valid[field.foreign_key] = getattr(valid[field_name], field.reference_key)
                except APIErrors as errors:
                    for error in errors:
                        error[0] = f'{attr_prefix}{field_name}.' + error[0]
                        api_errors.append(error)
                except APIError as error:
                    api_errors.append(error)
            elif field_key is not None and field_name is not None:
                try:
                    valid[field_key] = self._validate_field(field, field_name, values)
                except APIError as ex:
                    api_errors.append(ex)
        if api_errors:
            raise api_errors
        return valid

    @staticmethod
    def _validate_field(field: 'mapping.MappingObject', name: str, values: dict[str, Any]):
        if field.required and name not in values:
            raise exceptions.ParamMissingError(name)
        value = values.get(name, field.default)
        if not value and not field.nullable:
            raise exceptions.ParamNonNullableError(name)
        if value is not None and isinstance(field, mapping.Field):
            if field.type == types.db.Date:
                value = date_parser.parse(value)
        return value

    async def _validate_linked_entity(self, field: 'mapping.Reference', name: str,
                                      values: dict[str, Any], attr_prefix: str):
        model: core.Model = self.context.inject.require('model', field.model_name, immediate=True)
        repo = model.__props__.repo
        if name not in values:
            if field.required:
                raise exceptions.ParamMissingError(name)
            else:
                return None
        obj = values[name]
        if not isinstance(obj, dict):
            raise exceptions.BadParamFormatError(name, 'dict')
        field_def = self.context.mapper.payload(field.model_name, field.model_key)
        cols = [field_def[col.name] for col in model.__props__.entity_key]
        keys = dict((col.key, obj.get(col.name, None)) for col in cols)
        entity = await repo.query().filter_by(**keys).first()
        if entity is None:
            if not field.create_if_not_found:
                raise exceptions.EntityNotFoundError(field.model_name, ','.join(keys.keys()), ','.join(keys.values()))
            return await self.validate_payload(field.model_name, field.model_key, obj,
                                               patch=False, attr_prefix=attr_prefix)
        return entity
