from sqlalchemy import desc

from bolinette import validate, db, mapper
from bolinette.exceptions import EntityNotFoundError

_services = {}


class BaseService:
    def __init__(self, model, name):
        self.model = model
        self.name = name
        _services[model] = self

    def service(self, model):
        return _services.get(model)

    def get(self, identifier):
        entity = self.model.query.get(identifier)
        if entity is None:
            raise EntityNotFoundError(model=self.name, key='id', value=identifier)
        return entity

    def get_by(self, key, value):
        return self.model.query.filter_by(**{key: value}).all()

    def get_first_by(self, key, value):
        entity = self.model.query.filter_by(**{key: value}).first()
        if entity is None:
            raise EntityNotFoundError(model=self.name, key=key, value=value)
        return entity

    def get_by_criteria(self, criteria):
        return self.model.query.filter(criteria).all()

    def get_all(self, pagination=None, order_by=[]):
        query = self.model.query
        if len(order_by) > 0:
            query = BaseService.build_order_by(self.model, query, order_by)
        if pagination is not None:
            return query.paginate(**pagination)
        return query.all()

    def create(self, params):
        params = validate.model(self.model, params)
        entity = self.model(**params)
        db.session.add(entity)
        return entity

    def update(self, entity, params):
        mapper.update(self.model, entity, params)
        return entity

    def patch(self, entity, params):
        mapper.update(self.model, entity, params, patch=True)
        return entity

    def delete(self, entity):
        db.session.delete(entity)
        return entity

    @staticmethod
    def build_order_by(model, query, params):
        order_by_query = []
        for col_name, way in params:
            if hasattr(model, col_name):
                column = getattr(model, col_name)
                if way:
                    order_by_query.append(column)
                else:
                    order_by_query.append(desc(column))
        return query.order_by(*order_by_query)
