import re

from pymongo import MongoClient

from bolinette.blnt.database.engines import DatabaseEngine

_COLLECTION_REGEX = re.compile(r'^([^/]+://[^/]+/?)(.*)$')


class CollectionDatabase(DatabaseEngine):
    def __init__(self, uri):
        super().__init__(relational=False)
        db = 'bolinette'
        if match := _COLLECTION_REGEX.match(uri):
            uri = match.group(1)
            db = match.group(2) or db
        self.client = MongoClient(uri)
        self.db = self.client[db]

    async def open_transaction(self):
        pass

    async def close_transaction(self):
        pass

    async def rollback_transaction(self):
        pass

    async def create_all(self):
        pass

    async def drop_all(self):
        for collection in self.db.list_collection_names():
            self.db[collection].delete_many({})
