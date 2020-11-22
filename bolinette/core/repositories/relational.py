from bolinette import blnt, core
from bolinette.blnt.database import Pagination
from bolinette.core.repositories import Repository


class RelationalRepository(Repository):
    def __init__(self, name: str, model: 'core.Model', context: 'blnt.BolinetteContext'):
        super().__init__(name, model, context)
        self.database: 'blnt.database.RelationalDatabase' = context.db[model.__blnt__.database]
        self.table = context.table(name)

    def __repr__(self):
        return f'<Repository {self.name}>'

    @property
    def query(self):
        return self.database.session.query(self.table)

    async def get_all(self, pagination=None, order_by=None):
        if order_by is None:
            order_by = []
        query = self.query
        if len(order_by) > 0:
            query = await self._build_order_by(query, order_by)
        if pagination is not None:
            return self._paginate(query, pagination)
        return query.all()

    async def get(self, identifier):
        return self.query.get(identifier)

    async def get_by(self, key, value):
        return self.query.filter_by(**{key: value}).all()

    async def get_first_by(self, key, value):
        return self.query.filter_by(**{key: value}).first()

    async def get_by_criteria(self, criteria):
        return self.query.filter(criteria).all()

    async def create(self, values):
        filtered = await self._validate_model(values)
        entity = self.table(**filtered)
        self.database.session.add(entity)
        return entity

    async def update(self, entity, values):
        await self._map_model(entity, values)
        return entity

    async def patch(self, entity, values):
        await self._map_model(entity, values, patch=True)
        return entity

    async def delete(self, entity):
        self.database.session.delete(entity)
        return entity

    async def _build_order_by(self, query, params):
        order_by_query = []
        for col_name, way in params:
            if hasattr(self.table, col_name):
                column = getattr(self.table, col_name)
                if way:
                    order_by_query.append(column)
                else:
                    order_by_query.append(core.functions.desc(column))
        return query.order_by(*order_by_query)

    @staticmethod
    def _paginate(query, pagination):
        page = pagination['page']
        per_page = pagination['per_page']
        total = query.count()
        items = query.offset(page * per_page).limit(per_page).all()
        return Pagination(items, page, per_page, total)
