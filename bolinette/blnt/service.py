from datetime import datetime

from bolinette import core, blnt, utils
from bolinette.exceptions import EntityNotFoundError


class Service:
    __blnt__: 'ServiceMetadata' = None

    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context

    def __repr__(self):
        return f'<Service {self.__blnt__.name}>'

    @property
    def repo(self) -> blnt.Repository:
        return self.context.repo(self.__blnt__.model_name)

    async def get(self, identifier, *, safe=False):
        entity = await self.repo.get(identifier)
        if entity is None and not safe:
            raise EntityNotFoundError(model=self.__blnt__.name, key='id', value=identifier)
        return entity

    async def get_by(self, key, value):
        return await self.repo.get_by(key, value)

    async def get_first_by(self, key, value, *, safe=False):
        entity = await self.repo.get_first_by(key, value)
        if entity is None and not safe:
            raise EntityNotFoundError(model=self.__blnt__.name, key=key, value=value)
        return entity

    async def get_all(self, pagination=None, order_by=None):
        if order_by is None:
            order_by = []
        query = self.repo.query
        if len(order_by) > 0:
            query = await self._build_order_by(query, order_by)
        if pagination is not None:
            return await self._paginate(query, pagination)
        return query.all()

    async def create(self, values):
        return await self.repo.create(values)

    async def update(self, entity, values):
        return await self.repo.update(entity, values)

    async def patch(self, entity, values):
        return await self.repo.patch(entity, values)

    async def delete(self, entity):
        return await self.repo.delete(entity)

    async def _build_order_by(self, query, params):
        table = self.repo.table
        order_by_query = []
        for col_name, way in params:
            if hasattr(table, col_name):
                column = getattr(table, col_name)
                if way:
                    order_by_query.append(column)
                else:
                    order_by_query.append(blnt.functions.desc(column))
        return query.order_by(*order_by_query)

    @staticmethod
    async def _paginate(query, pagination):
        page = pagination['page']
        per_page = pagination['per_page']
        total = query.count()
        items = query.offset(page * per_page).limit(per_page).all()
        return utils.Pagination(items, page, per_page, total)


class SimpleService:
    __blnt__: 'ServiceMetadata' = None

    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context

    def __repr__(self):
        return f'<Service {self.__blnt__.name}>'


class ServiceMetadata:
    def __init__(self, name: str, model_name: str):
        self.name = name
        self.model_name = model_name


class HistorizedService(Service):
    def __init__(self, context: 'core.BolinetteContext'):
        super().__init__(context)

    async def create(self, values, *, current_user=None):
        if current_user:
            now = datetime.utcnow()
            values['created_on'] = now
            values['created_by_id'] = current_user.id
            values['updated_on'] = now
            values['updated_by_id'] = current_user.id
        return await super().create(values)

    async def update(self, entity, values, *, current_user=None):
        if current_user:
            now = datetime.utcnow()
            values['created_on'] = entity.created_on
            values['created_by_id'] = entity.created_by_id
            values['updated_on'] = now
            values['updated_by_id'] = current_user.id
        return await super().update(entity, values)

    async def patch(self, entity, values, *, current_user=None):
        if current_user:
            now = datetime.utcnow()
            values['updated_on'] = now
            values['updated_by_id'] = current_user.id
        return await super().patch(entity, values)
