from typing import Any, Generic, TypeVar

from bolinette.core import abc, BolinetteContext
from bolinette.core.objects import Pagination, PaginationParams, OrderByParams
from bolinette.data import DataContext, WithDataContext, Model, Entity
from bolinette.data.models import Relationship
from bolinette.data.database.queries import (
    BaseQuery,
    BaseQueryBuilder,
    RelationalQueryBuilder,
    CollectionQueryBuilder,
)
from bolinette.exceptions import ParamConflictError, APIErrors, ParamNonNullableError
from bolinette.utils.functions import setattr_, getattr_, invoke


T_Entity = TypeVar("T_Entity", bound=Entity)


class Repository(abc.WithContext, WithDataContext, Generic[T_Entity]):
    def __init__(
        self, context: BolinetteContext, data_ctx: DataContext, model: Model[T_Entity]
    ):
        abc.WithContext.__init__(self, context)
        WithDataContext.__init__(self, data_ctx)
        self._model = model
        self._query_builder = self._get_query_builder(model)

    @property
    def model(self) -> Model[T_Entity]:
        return self._model

    def _get_query_builder(self, model: Model[T_Entity]) -> BaseQueryBuilder[T_Entity]:
        db = self.data_ctx.db[model.__blnt__.database]
        if db.relational:
            return RelationalQueryBuilder(model, self.data_ctx)
        return CollectionQueryBuilder(model, self.data_ctx)

    def __repr__(self):
        return f"<Repository {self._model.__blnt__.name}>"

    def query(self):
        return self._query_builder.query()

    async def get_all(
        self, pagination: PaginationParams = None, order_by: list[OrderByParams] = None
    ):
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

    async def create(self, values: dict[str, Any], **kwargs):
        await self._call_mixin_methods("create", self, values=values, **kwargs)
        filtered = await self._validate_model(values, kwargs)
        entity = await self._query_builder.insert_entity(filtered)
        return entity

    async def update(self, entity, values: dict[str, Any], **kwargs):
        await self._call_mixin_methods(
            "update", self, entity=entity, values=values, **kwargs
        )
        await self._map_model(entity, values)
        return await self._query_builder.update_entity(entity)

    async def patch(self, entity, values: dict[str, Any], **kwargs):
        await self._call_mixin_methods(
            "patch", self, entity=entity, values=values, **kwargs
        )
        await self._map_model(entity, values, patch=True)
        return await self._query_builder.update_entity(entity)

    async def delete(self, entity, **kwargs):
        await self._call_mixin_methods("delete", self, entity=entity, **kwargs)
        return await self._query_builder.delete_entity(entity)

    @staticmethod
    async def _paginate(query: BaseQuery, pagination: PaginationParams):
        page = pagination.page
        per_page = pagination.per_page
        total = await query.count()
        items = await query.offset(page * per_page).limit(per_page).all()
        return Pagination(items, page, per_page, total)

    async def _validate_model(self, values: dict[str, Any], repo_args: dict[str, Any]):
        api_errors = APIErrors()
        ignore_keys: list[str] = []
        for _, relationship in self._model.__props__.get_relationships():
            await self._validate_linked_model(
                relationship, values, repo_args, ignore_keys
            )
        for _, column in self._model.__props__.get_columns():
            key = column.name
            if column.auto_increment or key in ignore_keys:
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

    @staticmethod
    async def _validate_linked_model(
        relationship: Relationship,
        values: dict[str, Any],
        repo_args: dict[str, Any],
        ignore_keys: list[str],
    ):
        if relationship.foreign_key is None:
            return
        foreign_key = relationship.foreign_key.name
        if values.get(foreign_key) is not None:
            return
        key = relationship.name
        if key in values:
            ignore_keys.append(foreign_key)
            linked = values[key]
            if isinstance(linked, dict):
                values[key] = await relationship.target_model.__repo__.create(
                    values[key], **repo_args
                )

    async def _map_model(self, entity, values: dict[str, Any], patch=False):
        api_errors = APIErrors()
        for _, column in self._model.__props__.get_columns():
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

    async def _call_mixin_methods(self, method_name: str, *args, **kwargs):
        for _, mixin in self._model.__props__.mixins.items():
            if method_name in mixin:
                await invoke(mixin[method_name].func, *args, **kwargs)
