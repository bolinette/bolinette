from typing import Generic, TypeVar
import sqlalchemy
from sqlalchemy import orm as sqlalchemy_orm

from bolinette import data
from bolinette.data.database.engines import RelationalDatabase
from bolinette.data.database.queries import BaseQueryBuilder, BaseQuery
from bolinette.exceptions import InternalError


T_Entity = TypeVar("T_Entity", bound=data.Entity)


class RelationalQueryBuilder(BaseQueryBuilder[T_Entity], Generic[T_Entity]):
    def __init__(self, model: "data.Model", data_ctx: data.DataContext):
        super().__init__(model, data_ctx)
        if isinstance(
            database := data_ctx.db[model.__blnt__.database], RelationalDatabase
        ):
            self._database: RelationalDatabase = database
        else:
            raise TypeError(
                f'Database engine for "{model.__blnt__.name}" model has to be relation based'
            )
        self._table = self._database.table(model.__blnt__.name)

    def query(self) -> "BaseQuery":
        return RelationalQuery(self._database, self._table)

    async def insert_entity(self, values):
        entity = self._table(**values)
        self._database.session.add(entity)
        return entity

    async def update_entity(self, entity):
        return entity

    async def delete_entity(self, entity):
        self._database.session.delete(entity)
        return entity


class RelationalQuery(BaseQuery[T_Entity], Generic[T_Entity]):
    def __init__(self, database: RelationalDatabase, table):
        super().__init__()
        self._database = database
        self._table = table

    def _clone(self) -> "RelationalQuery[T_Entity]":
        query = RelationalQuery(self._database, self._table)
        self._base_clone(query)
        return query

    async def all(self):
        return self._build_query().all()

    async def first(self):
        return self._build_query().first()

    async def get_by_id(self, identifier):
        return self._query().get(identifier)

    async def count(self):
        return self._build_query().count()

    def _query(self) -> sqlalchemy_orm.Query:
        return self._database.session.query(self._table)

    def _build_filters_by(self, query: sqlalchemy_orm.Query) -> sqlalchemy_orm.Query:
        for key, value in self._filters_by.items():
            path = key.split(".")
            if len(path) == 1:
                query = query.filter(getattr(self._table, key) == value)
            elif len(path) == 2:
                query = query.filter(
                    getattr(self._table, path[0]).has(**{path[1]: value})
                )
            else:
                raise InternalError(f"internal.query.wrong_entity_key_path:{key}")
        return query

    def _build_query(self):
        query = self._query()
        if len(self._filters_by) > 0:
            query = self._build_filters_by(query)
        if len(self._filters) > 0:
            for function in self._filters:
                query = query.filter(function(self._table))
        if len(self._order_by) > 0:
            for column, desc in self._order_by:
                if hasattr(self._table, column):
                    col = getattr(self._table, column)
                    if desc:
                        col = sqlalchemy.desc(col)
                    query = query.order_by(col)
        query = query.offset(self._offset)
        if self._limit is not None:
            query = query.limit(self._limit)
        return query
