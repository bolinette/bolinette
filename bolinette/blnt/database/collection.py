from pymongo import MongoClient

from bolinette.blnt.database import DatabaseEngine


class CollectionDatabase(DatabaseEngine):
    def __init__(self, uri):
        super().__init__(relational=False)
        self.client = MongoClient(uri)
        self.db = self.client['bolinette']

    async def open_transaction(self):
        pass

    async def close_transaction(self):
        pass

    async def rollback_transaction(self):
        pass

    async def create_all(self):
        pass

    async def drop_all(self):
        pass
