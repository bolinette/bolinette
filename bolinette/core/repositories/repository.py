from bolinette import blnt, core
from bolinette.exceptions import APIErrors, ParamConflictError
from bolinette.utils.functions import getattr_, setattr_


class Repository:
    def __init__(self, name: str, model: 'core.Model', context: 'blnt.BolinetteContext'):
        self.name = name
        self.model = model
        self.context = context

    async def get_all(self, pagination=None, order_by=None):
        raise NotImplementedError()

    async def get(self, identifier):
        raise NotImplementedError()

    async def get_by(self, key, value):
        raise NotImplementedError()

    async def get_first_by(self, key, value):
        raise NotImplementedError()

    async def get_by_criteria(self, criteria):
        raise NotImplementedError()

    async def create(self, values):
        raise NotImplementedError()

    async def update(self, entity, values):
        raise NotImplementedError()

    async def patch(self, entity, values):
        raise NotImplementedError()

    async def delete(self, entity):
        raise NotImplementedError()

    async def _validate_model(self, values: dict):
        api_errors = APIErrors()
        for column in self.model.__props__.get_columns().values():
            key = column.name
            if column.primary_key:
                continue
            if key in values:
                value = values.get(key)
                if column.unique:
                    if await self.get_first_by(column.name, value) is not None:
                        api_errors.append(ParamConflictError(key, value))
        if api_errors:
            raise api_errors
        return values

    async def _map_model(self, entity, values, patch=False):
        api_errors = APIErrors()
        for _, column in self.model.__props__.get_columns().items():
            key = column.name
            if column.primary_key or (key not in values and patch):
                continue
            original = getattr_(entity, key, None)
            new = values.get(key, None)
            if original == new:
                continue
            if column.unique and new is not None:
                if await self.get_first_by(column.name, new) is not None:
                    api_errors.append(ParamConflictError(key, new))
            setattr_(entity, key, new)
        if api_errors:
            raise api_errors
