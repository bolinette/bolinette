from datetime import datetime

from bolinette import core, types, exceptions, blnt
from bolinette.exceptions import APIErrors, APIError, EntityNotFoundError


class Validator:
    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context

    def validate_payload(self, model: str, key: str, values, patch=False):
        api_errors = APIErrors()
        valid = {}
        definition = self.context.mapping.payload(model, key)
        for field in definition.fields:
            field_key = None
            field_name = None
            if isinstance(field, types.mapping.Field):
                field_key = field.key
                field_name = field.name
            elif isinstance(field, types.mapping.Reference):
                field_key = field.foreign_key
                field_name = field.foreign_key
            if patch and field_name not in values:
                continue
            if field_key is not None and field_name is not None:
                try:
                    valid[field_key] = self._validate_field(field, field_name, values)
                except APIError as ex:
                    api_errors.append(ex)
        if api_errors:
            raise api_errors
        return valid

    def _validate_field(self, field, name, values):
        if field.required and name not in values:
            raise exceptions.ParamMissingError(name)
        value = values.get(name, field.default)
        if not value and not field.nullable:
            raise exceptions.ParamNonNullableError(name)
        if value is not None and isinstance(field, types.mapping.Field):
            if field.type == types.db.Date:
                value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        return value

    async def link_foreign_entities(self, model: str, key: str, params):
        api_errors = APIErrors()
        definition = self.context.mapping.payload(model, key)
        for field in definition.fields:
            if isinstance(field, types.mapping.Reference):
                value = params.get(field.foreign_key, None)
                repo: blnt.Repository = self.context.repo(field.reference_model)
                if value is not None and repo is not None:
                    entity = await repo.get_first_by(field.reference_key, value)
                    if entity is None:
                        api_errors.append(EntityNotFoundError(field.reference_model, field.reference_key, value))
        if api_errors:
            raise api_errors
