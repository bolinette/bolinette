from typing import Literal

from bolinette import core, blnt, mapping, types
from bolinette.exceptions import InternalError
from bolinette.utils.functions import getattr_, hasattr_, invoke


class Mapper:
    def __init__(self):
        self._payloads: dict[str, dict[str, mapping.Definition]] = {}
        self._responses: dict[str, dict[str, mapping.Definition]] = {}

    @staticmethod
    def _get_def(collection, model_name, key) -> 'mapping.Definition':
        m = collection.get(model_name)
        if m is None:
            raise InternalError(f'mapping.unknown_model:{model_name}')
        d = m.get(key)
        if d is None:
            raise InternalError(f'mapping.unknown_definition:{key}')
        return d

    def payload(self, model_name: str, key: str):
        return self._get_def(self._payloads, model_name, key)

    @property
    def payloads(self):
        for model_name in self._payloads:
            for key in self._payloads[model_name]:
                yield model_name, key, self._payloads[model_name][key]

    def response(self, model_name: str, key: str):
        return self._get_def(self._responses, model_name, key)

    @property
    def responses(self):
        for model_name in self._responses:
            for key in self._responses[model_name]:
                yield model_name, key, self._responses[model_name][key]

    def _extract_defs(self, model: 'core.Model', model_cls: type['core.Model'],
                      collection: Literal['payloads', 'responses'],
                      merge_defs: Literal['ignore', 'append', 'overwrite']):
        defs = {}
        for parent in model_cls.__bases__:
            if issubclass(parent, core.Model) and parent != core.Model:
                for _key, _def in self._extract_defs(model, parent, collection, merge_defs).items():
                    defs[_key] = _def
        def_func = getattr(model_cls, collection)
        if hasattr_(def_func, '__func__'):
            def_func = def_func.__func__
        def_gen = def_func(model)
        if def_gen is None:
            return defs
        new_defs = list(def_gen)
        for _def in new_defs:
            if isinstance(_def, list):
                model_key = 'default'
                payload = _def
            else:
                model_key, payload = _def
            if model_key in defs:
                if merge_defs == 'append':
                    for _param in payload:
                        defs[model_key].append(_param)
                elif merge_defs == 'overwrite':
                    defs[model_key] = payload
            else:
                defs[model_key] = payload
        return defs

    def register(self, model: 'core.Model'):
        def create_defs(collection, attr_name: Literal['payloads', 'responses']):
            defs = self._extract_defs(model, type(model), attr_name, model.__blnt__.merge_defs)
            for model_key, payload in defs.items():
                definition = mapping.Definition(model.__blnt__.name, model_key)
                for field in payload:
                    definition.fields.append(field)
                if definition.model_name not in collection:
                    collection[definition.model_name] = {}
                collection[definition.model_name][definition.model_key] = definition

        create_defs(self._payloads, 'payloads')
        create_defs(self._responses, 'responses')

    def marshall(self, definition, entity, *, skip_none=False, as_list=False, use_foreign_key=False):
        if entity is None:
            return None
        if as_list:
            return [self.marshall(definition, e, skip_none=skip_none, as_list=False, use_foreign_key=use_foreign_key)
                    for e in entity]
        values = {}
        for field in definition.fields:
            self._marshall_object(values, field, entity, skip_none, use_foreign_key)
        return values

    def _marshall_object(self, values, field, entity, skip_none: bool, use_foreign_key: bool):
        if isinstance(field, mapping.Field):
            self._marshall_field(values, field, entity, skip_none)
        elif isinstance(field, mapping.Reference) and use_foreign_key:
            values[field.foreign_key] = getattr_(entity, field.foreign_key, None)
        elif isinstance(field, mapping.Definition):
            self._marshall_definition(values, field, entity, skip_none, use_foreign_key)
        elif isinstance(field, mapping.List):
            self._marshall_list(values, field, entity, skip_none, use_foreign_key)

    @staticmethod
    def _marshall_field(values, field: 'mapping.Field', entity, skip_none: bool):
        if field.function is not None:
            value = field.function(entity)
        else:
            value = getattr_(entity, field.key, None)
        if field.formatting is not None:
            value = field.formatting(value)
        if not skip_none or value is not None:
            values[field.name] = value

    def _marshall_definition(self, values, definition: 'mapping.Definition', entity,
                             skip_none: bool, use_foreign_key: bool):
        d = self.response(definition.model_name, definition.model_key)
        attr = None
        if definition.function and callable(definition.function):
            attr = definition.function(entity)
        elif hasattr_(entity, definition.name):
            attr = getattr_(entity, definition.name, None)
        values[definition.name] = self.marshall(d, attr, skip_none=skip_none, as_list=False,
                                                use_foreign_key=use_foreign_key)

    def _marshall_list(self, values, field: 'mapping.List', entity, skip_none: bool, use_foreign_key: bool):
        if field.function and callable(field.function):
            e_list = invoke(field.function, entity)
        else:
            e_list = getattr_(entity, field.name, None)
        elem = field.element
        if isinstance(elem, types.db.DataType):
            values[field.name] = [e for e in e_list]
        elif isinstance(elem, mapping.Definition):
            d = self.response(elem.model_name, elem.model_key)
            values[field.name] = self.marshall(d, e_list, skip_none=skip_none, as_list=True,
                                               use_foreign_key=use_foreign_key)
