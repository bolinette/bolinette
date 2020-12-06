from bson import ObjectId
from pymongo.collection import Collection

from bolinette import blnt, core
from bolinette.blnt.database.engines import CollectionDatabase
from bolinette.blnt.database.queries import BaseQueryBuilder, BaseQuery
from bolinette.blnt.objects import OrderByParams


class CollectionQueryBuilder(BaseQueryBuilder):
    def __init__(self, model: 'core.Model', context: 'blnt.BolinetteContext'):
        super().__init__(model, context)
        self._name = model.__blnt__.name
        self._database: 'CollectionDatabase' = context.db[model.__blnt__.database]
        self._collection = self._database.db[self._name]

    def query(self) -> 'BaseQuery':
        return CollectionQuery(self._collection)

    async def insert_entity(self, values):
        result = self._collection.insert_one(values)
        return self._collection.find_one({'_id': ObjectId(result.inserted_id)})

    async def delete_entity(self, entity):
        self._collection.delete_one({'_id': entity['_id']})
        return entity


class CollectionQuery(BaseQuery):
    def __init__(self, collection: Collection):
        super().__init__()
        self._collection = collection

    def _clone(self):
        query = CollectionQuery(self._collection)
        self._base_clone(query)
        return query

    def _order_by_from_params(self, params: OrderByParams):
        return self._order_by_func(lambda c: c[params.column], desc=not params.ascending)

    async def all(self):
        return self._collection.find(self._build_filters())

    async def first(self):
        return self._collection.find_one(self._build_filters())

    async def get_by_id(self, identifier):
        return self._collection.find_one({'_id': ObjectId(identifier)})

    async def count(self):
        pass

    def _build_filters(self):
        params = {}
        if len(self._filters) > 0:
            for key in self._filters:
                if key == '_id':
                    params[key] = ObjectId(self._filters[key])
                else:
                    params[key] = self._filters[key]
        return params
