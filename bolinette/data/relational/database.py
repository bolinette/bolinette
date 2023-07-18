from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bolinette.data.relational import SessionManager


class RelationalDatabase:
    def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
        self._base = base
        self._name = name
        self._engine = create_async_engine(uri, echo=echo)
        self._session_maker = async_sessionmaker(self._engine)
        self._sql_defs: dict[type[Any], type[DeclarativeBase]] = {}

    @property
    def name(self) -> str:
        return self._name

    def open_session(self, sessions: SessionManager) -> None:
        session = self._session_maker()
        sessions.add(self._name, session)

    async def create_all(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(self._base.metadata.create_all)

    async def dispose(self) -> None:
        await self._engine.dispose()
