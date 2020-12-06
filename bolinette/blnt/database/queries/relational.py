import re

import sqlalchemy

from bolinette import blnt, core
from bolinette.blnt.database.engines import RelationalDatabase
from bolinette.blnt.database.queries import BaseQueryBuilder, BaseQuery
from bolinette.blnt.objects import OrderByParams
from bolinette.exceptions import UnprocessableEntityError

_ATTRIBUTE_ERROR_PATTERN = re.compile(r'^type object \'([^\']*)\' has no attribute \'([^\']*)\'$')


class RelationalQueryBuilder(BaseQueryBuilder):
    def __init__(self, model: 'core.Model', context: 'blnt.BolinetteContext'):
        super().__init__(model, context)
        self._database: RelationalDatabase = context.db[model.__blnt__.database]
        self._table = self.context.table(model.__blnt__.name)

    def query(self) -> 'BaseQuery':
        return RelationalQuery(self._database, self._table)

    async def insert_entity(self, values):
        entity = self._table(**values)
        self._database.session.add(entity)
        return entity

    async def delete_entity(self, entity):
        self._database.session.delete(entity)
        return entity


class RelationalQuery(BaseQuery):
    def __init__(self, database: RelationalDatabase, table):
        super().__init__()
        self._database = database
        self._table = table

    def _clone(self):
        query = RelationalQuery(self._database, self._table)
        self._base_clone(query)
        return query

    def _order_by_from_params(self, params: OrderByParams):
        return self._order_by_func(lambda t: getattr(t, params.column), desc=not params.ascending)

    async def all(self):
        return self._build_query().all()

    async def first(self):
        return self._build_query().first()

    async def get_by_id(self, identifier):
        return self._query().get(identifier)

    async def count(self):
        return self._build_query().count()

    def _query(self):
        return self._database.session.query(self._table)

    def _build_query(self):
        query = self._query()
        if len(self._filters) > 0:
            query = query.filter_by(**self._filters)
        if len(self._order_by):
            for func, desc in self._order_by:
                try:
                    col = func(self._table)
                except AttributeError as e:
                    message = _ATTRIBUTE_ERROR_PATTERN.match(e.args[0])
                    raise UnprocessableEntityError(f'{message.group(1)}.no_column_in_entity:{message.group(2)}')
                if desc:
                    col = sqlalchemy.desc(col)
                query = query.order_by(col)
        return query
