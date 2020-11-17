class DatabaseEngine:
    def __init__(self, relational: bool):
        self.relational = relational

    async def open_transaction(self):
        raise NotImplementedError()

    async def close_transaction(self):
        raise NotImplementedError()

    async def rollback_transaction(self):
        raise NotImplementedError()

    async def create_all(self):
        raise NotImplementedError()

    async def drop_all(self):
        raise NotImplementedError()
