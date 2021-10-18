from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bolinette.blnt.database.engines import DatabaseEngine
from bolinette.exceptions import InternalError


class RelationalDatabase(DatabaseEngine):
    def __init__(self, uri):
        super().__init__(relational=True)
        self._engine = create_engine(uri, echo=False)
        self._base = declarative_base()
        self._Session = sessionmaker(bind=self._engine)
        self._session = self._Session()
        self._tables = {}

    @property
    def base(self):
        return self._base

    @property
    def session(self):
        return self._session

    def add_table(self, key: str, table):
        self._tables[key] = table

    def table(self, key: str):
        if key not in self._tables:
            raise InternalError(f'No table named {key} in database engine')
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
