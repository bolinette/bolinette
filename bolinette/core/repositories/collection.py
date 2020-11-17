from bolinette import blnt, core
from bolinette.core.repositories import Repository
from bolinette.exceptions import InternalError


class CollectionRepository(Repository):
    def __init__(self, name: str, model: 'core.Model', context: 'blnt.BolinetteContext'):
        super().__init__(name, model, context)
        self.database: 'blnt.database.CollectionDatabase' = context.db[model.__blnt__.database]
        self.table = context.table(name)

    async def get(self, identifier):
        raise InternalError('internal.feature.not_supported')

    async def get_by(self, key, value):
        raise InternalError('internal.feature.not_supported')

    async def get_first_by(self, key, value):
        raise InternalError('internal.feature.not_supported')

    async def get_by_criteria(self, criteria):
        raise InternalError('internal.feature.not_supported')

    async def create(self, values):
        raise InternalError('internal.feature.not_supported')

    async def update(self, entity, values):
        raise InternalError('internal.feature.not_supported')

    async def patch(self, entity, values):
        raise InternalError('internal.feature.not_supported')

    async def delete(self, entity):
        raise InternalError('internal.feature.not_supported')
