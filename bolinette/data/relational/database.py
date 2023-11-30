from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bolinette.data.relational import AsyncSession, AsyncTransaction


class RelationalDatabase:
    def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
        self._base = base
        self._name = name
        self._uri = uri
        self._engine = create_async_engine(uri, echo=echo)
        self._session_maker = async_sessionmaker(self._engine)
        self._sql_defs: dict[type[Any], type[DeclarativeBase]] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def in_memory(self) -> bool:
        return self._uri == "sqlite+aiosqlite://"

    def open_session(self, transaction: AsyncTransaction, /) -> None:
        session: AsyncSession[DeclarativeBase] = self._session_maker(expire_on_commit=False)  # pyright: ignore
        transaction.add(self._name, session)

    async def create_all(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(self._base.metadata.create_all)

    async def dispose(self) -> None:
        await self._engine.dispose()
