from abc import ABC, abstractmethod


class AbstractEngine(ABC):
    def __init__(self, relational: bool):
        self.relational = relational

    @abstractmethod
    async def open_transaction(self):
        ...

    @abstractmethod
    async def close_transaction(self):
        ...

    @abstractmethod
    async def rollback_transaction(self):
        ...

    @abstractmethod
    async def create_all(self):
        ...

    @abstractmethod
    async def drop_all(self):
        ...
