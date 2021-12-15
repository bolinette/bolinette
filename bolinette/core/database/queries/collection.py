from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.cursor import Cursor

from bolinette import abc, data
from bolinette.core.database.engines import CollectionDatabase
from bolinette.core.database.queries import BaseQueryBuilder, BaseQuery


class CollectionQueryBuilder(BaseQueryBuilder):
    def __init__(self, model: 'data.Model', context: abc.Context):
        super().__init__(model, context)
        self._name = model.__blnt__.name
        if isinstance(database := context.db[model.__blnt__.database], CollectionDatabase):
            self._database: CollectionDatabase = database
        else:
            raise TypeError(f'Database engine for "{model.__blnt__.name}" model has to be collection based')
        self._collection = self._database.db[self._name]

    def query(self) -> 'BaseQuery':
        return CollectionQuery(self._collection)

    async def insert_entity(self, values):
        result = self._collection.insert_one(values)
        return self._collection.find_one({'_id': ObjectId(result.inserted_id)})

    async def update_entity(self, entity):
        values = dict(entity)
        _id = values.pop('_id')
        self._collection.update_one({'_id': _id}, {'$set': values})
        return self._collection.find_one({'_id': ObjectId(_id)})

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

    async def all(self):
        return self._apply_params(self._collection.find(self._build_filters()))

    async def first(self):
        return self._collection.find_one(self._build_filters())

    async def get_by_id(self, identifier):
        return self._collection.find_one({'_id': ObjectId(identifier)})

    async def count(self):
        return self._collection.count_documents(self._build_filters())

    def _apply_params(self, cursor: Cursor):
        cursor.skip(self._offset)
        if self._limit is not None:
            cursor.limit(self._limit)
        if len(self._order_by) > 0:
            order_by = [(column, DESCENDING if desc else ASCENDING) for column, desc in self._order_by]
            cursor.sort(order_by)
        return cursor

    def _build_filters(self):
        params = {}
        if len(self._filters_by) > 0:
            for key in self._filters_by:
                if key == '_id':
                    params[key] = ObjectId(self._filters_by[key])
                else:
                    params[key] = self._filters_by[key]
        return params