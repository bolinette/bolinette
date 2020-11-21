from bson import ObjectId

from bolinette import blnt, core
from bolinette.core.repositories import Repository
from bolinette.exceptions import InternalError


class CollectionRepository(Repository):
    def __init__(self, name: str, model: 'core.Model', context: 'blnt.BolinetteContext'):
        super().__init__(name, model, context)
        self.database: 'blnt.database.CollectionDatabase' = context.db[model.__blnt__.database]

    @property
    def collection(self):
        return self.database.db[self.name]

    async def get_all(self, pagination=None, order_by=None):
        return self.collection.find()

    async def get(self, identifier):
        return self.collection.find_one({'_id': ObjectId(identifier)})

    async def get_by(self, key, value):
        if key == '_id':
            value = ObjectId(value)
        return self.collection.find({key: value})

    async def get_first_by(self, key, value):
        if key == '_id':
            value = ObjectId(value)
        return self.collection.find_one({key: value})

    async def get_by_criteria(self, criteria):
        raise InternalError('internal.feature.not_supported')

    async def create(self, values):
        result = self.collection.insert_one(values)
        return await self.get(result.inserted_id)

    async def update(self, entity, values):
        raise InternalError('internal.feature.not_supported')

    async def patch(self, entity, values):
        raise InternalError('internal.feature.not_supported')

    async def delete(self, entity):
        raise InternalError('internal.feature.not_supported')
