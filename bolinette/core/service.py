from typing import Any

from bolinette import abc, blnt
from bolinette.blnt.objects import PaginationParams, OrderByParams
from bolinette.decorators import injected
from bolinette.exceptions import EntityNotFoundError


class SimpleService(abc.WithContext):
    __blnt__: 'ServiceMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)

    def __repr__(self):
        return f'<Service {self.__blnt__.name}>'


class Service(SimpleService):
    __blnt__: 'ServiceMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
    
    @injected
    def model(self, inject: abc.inject.Injection):
        return inject.require('model', self.__blnt__.model_name)
    
    @property
    def repo(self):
        return self.model.__props__.repo

    def __repr__(self):
        return f'<Service {self.__blnt__.name}>'

    async def get(self, identifier, *, safe=False):
        entity = await self.repo.get(identifier)
        if entity is None and not safe:
            raise EntityNotFoundError(model=self.__blnt__.name, key='id', value=identifier)
        return entity

    async def get_by(self, key: str, value):
        return await self.repo.get_by(key, value)

    async def get_first_by(self, key: str, value, *, safe=False):
        entity = await self.repo.get_first_by(key, value)
        if entity is None and not safe:
            raise EntityNotFoundError(model=self.__blnt__.name, key=key, value=value)
        return entity

    async def get_first_by_keys(self, keys: dict[str, Any], *, safe=False):
        entity = await self.repo.query().filter_by(**keys).first()
        if entity is None and not safe:
            key = ','.join(keys.keys())
            value = ','.join(keys.values())
            raise EntityNotFoundError(model=self.__blnt__.name, key=key, value=value)
        return entity

    async def get_all(self, *, pagination: PaginationParams = None, order_by: list[OrderByParams] = None):
        return await self.repo.get_all(pagination, order_by)

    async def create(self, values: dict[str, Any], **kwargs):
        return await self.repo.create(values, **kwargs)

    async def update(self, entity, values: dict[str, Any], **kwargs):
        return await self.repo.update(entity, values, **kwargs)

    async def patch(self, entity, values: dict[str, Any], **kwargs):
        return await self.repo.patch(entity, values, **kwargs)

    async def delete(self, entity, **kwargs):
        return await self.repo.delete(entity, **kwargs)


class ServiceMetadata:
    def __init__(self, name: str, model_name: str):
        self.name = name
        self.model_name = model_name
