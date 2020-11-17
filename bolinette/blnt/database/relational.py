from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bolinette.blnt.database import DatabaseEngine


class RelationalDatabase(DatabaseEngine):
    def __init__(self, uri):
        super().__init__(relational=True)
        self._engine = create_engine(uri, echo=False)
        self._factory = sessionmaker(bind=self._engine)
        self._base = declarative_base()
        self._session = self._factory()

    @property
    def base(self):
        return self._base

    @property
    def session(self):
        return self._session

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
