from bolinette import blnt, core
from bolinette.exceptions import APIErrors, ParamConflictError


class Repository:
    def __init__(self, name: str, model: core.Model, context: 'blnt.BolinetteContext'):
        self.name = name
        self.model = model
        self.database = context.db[model.__blnt__.database]
        self.table = context.table(name)

    def __repr__(self):
        return f'<Repository {self.name}>'

    @property
    def query(self):
        return self.database.session.query(self.table)

    def column(self, name: str):
        return getattr(self.table, name)

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
        self.database.session.add(entity)
        return entity

    async def update(self, entity, values):
        self._map_model(entity, values)
        return entity

    async def patch(self, entity, values):
        self._map_model(entity, values, patch=True)
        return entity

    async def delete(self, entity):
        self.database.session.delete(entity)
        return entity

    def _validate_model(self, values: dict):
        api_errors = APIErrors()
        for column in self.model.__props__.get_columns().values():
            key = column.name
            if column.primary_key:
                continue
            value = values.get(key, None)
            if column.unique and value is not None:
                if self.query.filter(self.column(key) == value).first() is not None:
                    api_errors.append(ParamConflictError(key, value))
        if api_errors:
            raise api_errors
        return values

    def _map_model(self, entity, values, patch=False):
        api_errors = APIErrors()
        for _, column in self.model.__props__.get_columns().items():
            key = column.name
            if column.primary_key or (key not in values and patch):
                continue
            original = getattr(entity, key)
            new = values.get(key, None)
            if original == new:
                continue
            if column.unique and new is not None:
                if self.query.filter(self.column(key) == new).first() is not None:
                    api_errors.append(ParamConflictError(key, new))
            setattr(entity, key, new)
        if api_errors:
            raise api_errors
