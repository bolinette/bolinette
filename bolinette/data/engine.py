from abc import ABC, abstractmethod

from sqlalchemy import Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class AbstractEngine(ABC):
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


class RelationalDatabase(AbstractEngine):
    def __init__(self, uri):
        super().__init__(relational=True)
        self._engine = create_engine(uri, echo=False)
        self._base = declarative_base()
        self._session = sessionmaker(bind=self._engine)()
        self._tables: dict[str, Table] = {}

    def add_table(self, key: str, table: Table):
        self._tables[key] = table

    def get_table(self, key: str):
        if key not in self._tables:
            raise KeyError(key)
        return self._tables[key]

    async def open_transaction(self):
        pass

    async def close_transaction(self):
        self._session.commit()

    async def rollback_transaction(self):
        self._session.rollback()

    async def create_all(self):
        self._base.metadata.create_all(self._engine)

    async def drop_all(self):
        self._base.metadata.drop_all(self._engine)
