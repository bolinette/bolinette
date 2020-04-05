from sqlalchemy import desc

from bolinette import mapping, db
from bolinette.exceptions import EntityNotFoundError
from bolinette.utils import Pagination

_services = {}


class BaseService:
    def __init__(self, model):
        self.model = model
        self.name = model.__tablename__.lower()
        _services[model] = self

    def service(self, model):
        return _services.get(model)

    async def get(self, identifier, **_):
        entity = db.engine.session.query(self.model).get(identifier)
        if entity is None:
            raise EntityNotFoundError(model=self.name, key='id', value=identifier)
        return entity

    async def get_by(self, key, value, **_):
        return db.engine.session.query(self.model).filter_by(**{key: value}).all()

    async def get_first_by(self, key, value, **_):
        entity = db.engine.session.query(self.model).filter_by(**{key: value}).first()
        if entity is None:
            raise EntityNotFoundError(model=self.name, key=key, value=value)
        return entity

    async def get_by_criteria(self, criteria, **_):
        return db.engine.session.query(self.model).filter(criteria).all()

    async def get_all(self, pagination=None, order_by=None, **_):
        if order_by is None:
            order_by = []
        query = db.engine.session.query(self.model)
        if len(order_by) > 0:
            query = await BaseService._build_order_by(self.model, query, order_by)
        if pagination is not None:
            return await BaseService._paginate(query, pagination)
        return query.all()

    async def create(self, params, **_):
        params = mapping.validate_model(self.model, params)
        entity = self.model(**params)
        db.engine.session.add(entity)
        return entity

    async def update(self, entity, params, **_):
        mapping.map_model(self.model, entity, params)
        return entity

    async def patch(self, entity, params, **_):
        mapping.map_model(self.model, entity, params, patch=True)
        return entity

    async def delete(self, entity, **_):
        db.engine.session.delete(entity)
        return entity

    @staticmethod
    async def _build_order_by(model, query, params):
        order_by_query = []
        for col_name, way in params:
            if hasattr(model, col_name):
                column = getattr(model, col_name)
                if way:
                    order_by_query.append(column)
                else:
                    order_by_query.append(desc(column))
        return query.order_by(*order_by_query)

    @staticmethod
    async def _paginate(query, pagination):
        page = pagination['page']
        per_page = pagination['per_page']
        total = query.count()
        items = query.offset(page * per_page).limit(per_page).all()
        return Pagination(items, page, per_page, total)


class SimpleService:
    def __init__(self, name):
        self.name = name
        _services[name] = self
