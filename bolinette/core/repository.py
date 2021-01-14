from typing import List, Dict, Any

from bolinette import blnt, core
from bolinette.blnt.objects import Pagination, PaginationParams, OrderByParams
from bolinette.blnt.database.queries import BaseQuery, RelationalQueryBuilder, CollectionQueryBuilder
from bolinette.exceptions import ParamConflictError, APIErrors, ParamNonNullableError
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
                query = query.order_by(order.column, desc=not order.ascending)
        if pagination is not None:
            return await self._paginate(query, pagination)
        return await query.all()

    async def get(self, identifier):
        return await self.query().get_by_id(identifier)

    async def get_by(self, key: str, value):
        return await self.query().filter_by(**{key: value}).all()

    async def get_first_by(self, key: str, value):
        return await self.query().filter_by(**{key: value}).first()

    async def create(self, values: Dict[str, Any]):
        filtered = await self._validate_model(values)
        entity = await self._query_builder.insert_entity(filtered)
        return entity

    async def update(self, entity, values: Dict[str, Any]):
        await self._map_model(entity, values)
        return await self._query_builder.update_entity(entity)

    async def patch(self, entity, values: Dict[str, Any]):
        await self._map_model(entity, values, patch=True)
        return await self._query_builder.update_entity(entity)

    async def delete(self, entity):
        return await self._query_builder.delete_entity(entity)

    @staticmethod
    async def _paginate(query: BaseQuery, pagination: PaginationParams):
        page = pagination.page
        per_page = pagination.per_page
        total = await query.count()
        items = await query.offset(page * per_page).limit(per_page).all()
        return Pagination(items, page, per_page, total)

    async def _validate_model(self, values: Dict[str, Any]):
        api_errors = APIErrors()
        ignore_keys = []
        for _, relationship in self.model.__props__.get_relationships():
            key = relationship.name
            if key in values and values[key] is not None:
                ignore_keys.append(relationship.foreign_key.name)
        for _, column in self.model.__props__.get_columns():
            key = column.name
            if column.primary_key or key in ignore_keys:
                continue
            if key in values:
                value = values.get(key)
                if value is None and not column.nullable:
                    api_errors.append(ParamNonNullableError(key))
                if column.unique:
                    if await self.get_first_by(column.name, value) is not None:
                        api_errors.append(ParamConflictError(key, value))
            elif not column.nullable:
                api_errors.append(ParamNonNullableError(key))
        if api_errors:
            raise api_errors
        return values

    async def _map_model(self, entity, values: Dict[str, Any], patch=False):
        api_errors = APIErrors()
        for _, column in self.model.__props__.get_columns():
            key = column.name
            if column.primary_key or (key not in values and patch):
                continue
            original = getattr_(entity, key, None)
            new = values.get(key, None)
            if original == new:
                continue
            if new is None and not column.nullable:
                api_errors.append(ParamNonNullableError(key))
            if column.unique and new is not None:
                if await self.get_first_by(column.name, new) is not None:
                    api_errors.append(ParamConflictError(key, new))
            setattr_(entity, key, new)
        if api_errors:
            raise api_errors
