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

    def get_all(self):
        return self.model.query.all()

    def create(self, params):
        params = validate.model(self.model, params)
        entity = self.model(**params)
        db.session.add(entity)
        return entity

    def update(self, entity, params):
        mapper.update(self.model, entity, params)
        return entity

    def delete(self, entity):
        db.session.delete(entity)
        return entity
