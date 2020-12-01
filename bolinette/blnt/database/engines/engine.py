from abc import ABC, abstractmethod


class DatabaseEngine(ABC):
    def __init__(self, relational: bool):
        self.relational = relational

    @abstractmethod
    async def open_transaction(self):
        pass

    @abstractmethod
    async def close_transaction(self):
        pass

    @abstractmethod
    async def rollback_transaction(self):
        pass

    @abstractmethod
    async def create_all(self):
        pass

    @abstractmethod
    async def drop_all(self):
        pass
