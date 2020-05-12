from bolinette import core, data
from bolinette.exceptions import ParamConflictError


class Repository:
    def __init__(self, name: str, model: data.Model, context: 'core.BolinetteContext'):
        self.name = name
        self.model = model
        self.table = context.table(name)
        self.db = context.db

    def __repr__(self):
        return f'<Repository {self.name}>'

    @property
    def query(self):
        return self.db.session.query(self.table)

    async def get(self, identifier):
        return self.query.get(identifier)

    async def get_by(self, key, value):
        return self.query.filter_by(**{key: value}).all()

    async def get_first_by(self, key, value):
        return self.query.filter_by(**{key: value}).first()

    async def get_by_criteria(self, criteria):
        return self.query.filter(criteria).all()

    async def create(self, values):
        filtered = self._validate_model(values)
        entity = self.table(**filtered)
        self.db.session.add(entity)
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

    def _validate_model(self, params: dict):
        errors = []
        for column in self.model.__blnt__.get_columns().values():
            key = column.name
            if column.primary_key:
                continue
            value = params.get(key, None)
            if column.unique and value is not None:
                if self.query.filter(column == value).first() is not None:
                    errors.append((key, value))
        if len(errors) > 0:
            raise ParamConflictError(params=errors)
        return params
