from bolinette import validate, db, mapper
from bolinette.exceptions import EntityNotFoundError

_services = {}


class BaseService:
    def __init__(self, model):
        self.model = model
        self.name = model.__name__.lower()
        _services[model] = self

    def service(self, model):
        return _services.get(model)

    def get(self, identifier):
        entity = self.model.query.get(identifier)
        if entity is None:
            raise EntityNotFoundError(model=self.name, key='id', value=identifier)
        return entity

    def get_by(self, key, value):
        entity = self.model.query.filter_by(**{key: value}).first()
        if entity is None:
            raise EntityNotFoundError(model=self.name, key=key, value=value)
        return entity

    def get_by_criteria(self, criteria, key, value):
        entity = self.model.query.filter(criteria).first()
        if entity is None:
            raise EntityNotFoundError(model=self.name, key=key, value=value)
        return entity

    def create(self, **kwargs):
        params = validate.model(self.model, kwargs)
        entity = self.model(**params)
        db.session.add(entity)
        return entity

    def update(self, entity, **kwargs):
        mapper.update(self.model, entity, kwargs)
        return entity

    def delete(self, entity):
        db.session.delete(entity)
        return entity
