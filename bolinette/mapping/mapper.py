from typing import Dict

from bolinette import core, blnt, mapping
from bolinette.exceptions import InternalError
from bolinette.utils.functions import getattr_, hasattr_


class Mapper:
    def __init__(self, context: 'blnt.BolinetteContext'):
        self.context = context
        self._payloads: Dict[str, mapping.Definition] = {}
        self._responses: Dict[str, mapping.Definition] = {}

    def _get_def(self, collection, model_name, key) -> 'mapping.Definition':
        m = collection.get(model_name)
        if m is None:
            raise InternalError(f'mapping.unknown_model:{model_name}')
        d = m.get(key)
        if d is None:
            raise InternalError(f'mapping.unknown_definition:{key}')
        return d

    def payload(self, model_name: str, key: str):
        return self._get_def(self._payloads, model_name, key)

    def response(self, model_name: str, key: str):
        return self._get_def(self._responses, model_name, key)

    def register(self, model_name: str, model: 'core.Model'):
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

        create_defs(self._payloads, model.payloads())
        create_defs(self._responses, model.responses())

    def marshall(self, definition, entity, *, skip_none=False, as_list=False, use_foreign_key=False):
        if not entity:
            return None
        if as_list:
            return [self.marshall(definition, e, skip_none=skip_none, as_list=False, use_foreign_key=use_foreign_key)
                    for e in entity]

        values = {}
        for field in definition.fields:
            if isinstance(field, mapping.Field):
                if field.function is not None:
                    value = field.function(entity)
                else:
                    value = getattr_(entity, field.key, None)
                if field.formatting is not None:
                    value = field.formatting(value)
                if not skip_none or value is not None:
                    values[field.name] = value
            elif isinstance(field, mapping.Reference) and use_foreign_key:
                values[field.foreign_key] = getattr_(entity, field.foreign_key, None)
            elif isinstance(field, mapping.Definition):
                d = self.response(field.model_name, field.model_key)
                attr = None
                if field.function and callable(field.function):
                    attr = field.function(entity)
                elif hasattr_(entity, field.name):
                    attr = getattr_(entity, field.name, None)
                values[field.name] = self.marshall(d, attr, skip_none=skip_none, as_list=False,
                                                   use_foreign_key=use_foreign_key)
            elif isinstance(field, mapping.List):
                d = self.response(field.element.model_name, field.element.model_key)
                values[field.name] = self.marshall(d, getattr_(entity, field.name, None), skip_none=skip_none,
                                                   as_list=True, use_foreign_key=use_foreign_key)
        return values
