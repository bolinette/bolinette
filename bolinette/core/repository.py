from typing import List

from bolinette import blnt, core
from bolinette.blnt.objects import Pagination, PaginationParams, OrderByParams
from bolinette.blnt.database.queries import RelationalQueryBuilder, CollectionQueryBuilder
from bolinette.exceptions import ParamConflictError, APIErrors
from bolinette.utils.functions import setattr_, getattr_


class Repository:
    def __init__(self, name: str, model: 'core.Model', context: 'blnt.BolinetteContext'):
        self.name = name
        self.model = model
        self.context = context
        self._query_builder = self._get_query_builder(model, context)

    @staticmethod
    def _get_query_builder(model: 'core.Model', context: 'blnt.BolinetteContext'):
        db = context.db[model.__blnt__.database]
        if db.relational:
            return RelationalQueryBuilder(model, context)
        return CollectionQueryBuilder(model, context)

    def __repr__(self):
        return f'<Repository {self.name}>'

    def query(self):
        return self._query_builder.query()

    async def get_all(self, pagination: PaginationParams = None, order_by: List[OrderByParams] = None):
        if order_by is None:
            order_by = []
        query = self.query()
        if len(order_by) > 0:
            for order in order_by:
                query = query.order_by_from_params(order)
        if pagination is not None:
            return await self._paginate(query, pagination)
        return await query.all()

    async def get(self, identifier):
        return await self.query().get_by_id(identifier)

    async def get_by(self, key, value):
        return await self.query().filter_by(**{key: value}).all()

    async def get_first_by(self, key, value):
        return await self.query().filter_by(**{key: value}).first()

    async def create(self, values):
        filtered = await self._validate_model(values)
        entity = await self._query_builder.insert_entity(filtered)
        return entity

    async def update(self, entity, values):
        await self._map_model(entity, values)
        return entity

    async def patch(self, entity, values):
        await self._map_model(entity, values, patch=True)
        return entity

    async def delete(self, entity):
        return await self._query_builder.delete_entity(entity)

    async def _paginate(self, query, pagination: PaginationParams):
        page = pagination.page
        per_page = pagination.per_page
        total = await query.count()
        items = await query.offset(page * per_page).limit(per_page).all()
        return Pagination(items, page, per_page, total)

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
