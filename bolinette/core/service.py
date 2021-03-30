from typing import List, Dict, Any

from bolinette import blnt
from bolinette.blnt.objects import PaginationParams, OrderByParams
from bolinette.exceptions import EntityNotFoundError
from bolinette.utils.functions import async_invoke


class Service:
    __blnt__: 'ServiceMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        self.__props__ = ServiceProps(self)
        self.context = context
        self.repo = context.repo(self.__blnt__.model_name)

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

    async def get_all(self, *, pagination: PaginationParams = None, order_by: List[OrderByParams] = None):
        return await self.repo.get_all(pagination, order_by)

    async def create(self, values: Dict[str, Any], **kwargs):
        await self.__props__.call_mixin_methods('create', self, values=values, **kwargs)
        return await self.repo.create(values)

    async def update(self, entity, values: Dict[str, Any], **kwargs):
        await self.__props__.call_mixin_methods('update', self, entity=entity, values=values, **kwargs)
        return await self.repo.update(entity, values)

    async def patch(self, entity, values: Dict[str, Any], **kwargs):
        await self.__props__.call_mixin_methods('patch', self, entity=entity, values=values, **kwargs)
        return await self.repo.patch(entity, values)

    async def delete(self, entity, **kwargs):
        await self.__props__.call_mixin_methods('delete', self, entity=entity, **kwargs)
        return await self.repo.delete(entity)


class SimpleService:
    __blnt__: 'ServiceMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        self.context = context

    def __repr__(self):
        return f'<Service {self.__blnt__.name}>'


class ServiceMetadata:
    def __init__(self, name: str, model_name: str):
        self.name = name
        self.model_name = model_name


class ServiceProps(blnt.Properties):
    async def call_mixin_methods(self, method_name: str, *args, **kwargs):
        for _, mixin in self.parent.repo.model.__props__.mixins.items():
            if method_name in mixin:
                await async_invoke(mixin[method_name].func, *args, **kwargs)
