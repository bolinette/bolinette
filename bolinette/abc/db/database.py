from abc import ABC, abstractmethod


class Engine(ABC):
    def __init__(self, relational: bool):
        self.relational = relational

    @abstractmethod
    async def open_transaction(self): ...

    @abstractmethod
    async def close_transaction(self): ...

    @abstractmethod
    async def rollback_transaction(self): ...

    @abstractmethod
    async def create_all(self): ...

    @abstractmethod
    async def drop_all(self): ...



class Manager(ABC):
    @abstractmethod
    async def open_transaction(self): ...

    @abstractmethod
    async def close_transaction(self): ...

    @abstractmethod
    async def rollback_transaction(self): ...

    @abstractmethod
    async def create_all(self): ...

    @abstractmethod
    async def drop_all(self): ...

    @abstractmethod
    async def run_seeders(self, log: bool = False, tab: int = 0): ...

    @abstractmethod
    def get_engine(self, name: str) -> Engine: ...

    @abstractmethod
    def __getitem__(self, key: str) -> Engine: ...

    @abstractmethod
    def __contains__(self, key: str) -> bool: ...
