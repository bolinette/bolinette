from abc import ABC, abstractmethod
from typing import override

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from bolinette.data.relational import AsyncTransaction, EntitySession


class AbstractDatabase(ABC):
    _session_maker: sessionmaker[Session] | async_sessionmaker[AsyncSession]

    def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
        self._base = base
        self._name = name
        self._uri = uri

    @property
    def name(self) -> str:
        return self._name

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def in_memory(self) -> bool:
        return self._uri in ("sqlite://", "sqlite+aiosqlite://")

    def open_session(self, transaction: AsyncTransaction, /) -> None:
        session: EntitySession[DeclarativeBase] = EntitySession(self._session_maker(expire_on_commit=False))
        transaction.add(self._name, session)

    @abstractmethod
    async def create_all(self) -> None: ...

    @abstractmethod
    async def dispose(self) -> None: ...


class RelationalDatabase(AbstractDatabase):
    def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
        super().__init__(base, name, uri, echo)
        self._engine = create_engine(uri, echo=echo)
        self._session_maker = sessionmaker(self._engine)

    @override
    async def create_all(self) -> None:
        self._base.metadata.create_all(self._engine)

    @override
    async def dispose(self) -> None:
        self._engine.dispose()


class AsyncRelationalDatabase(AbstractDatabase):
    def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
        super().__init__(base, name, uri, echo)
        self._engine = create_async_engine(uri, echo=echo)
        self._session_maker = async_sessionmaker(self._engine)

    @override
    async def create_all(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(self._base.metadata.create_all)

    @override
    async def dispose(self) -> None:
        await self._engine.dispose()
