from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import override

from sqlalchemy import create_engine, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from bolinette.data.relational._session import EntitySession


class AbstractDatabase(ABC):
    _session_maker: sessionmaker[Session] | async_sessionmaker[AsyncSession]

    def __init__(self, name: str, url: str, echo: bool, bases: Sequence[type[DeclarativeBase]]) -> None:
        self._name = name
        self._url = url
        self._echo = echo
        self._bases = [*bases]

    @property
    def name(self) -> str:
        return self._name

    @property
    def url(self) -> str:
        return self._url

    @property
    def echo(self) -> bool:
        return self._echo

    @property
    def bases(self) -> list[type[DeclarativeBase]]:
        return [*self._bases]

    @property
    def in_memory(self) -> bool:
        url = make_url(self._url)
        return url.get_backend_name() == "sqlite" and url.database in (None, "", ":memory:")

    def open_session(self) -> EntitySession[DeclarativeBase]:
        return EntitySession(self._session_maker(expire_on_commit=False))

    @abstractmethod
    async def create_all(self) -> None: ...

    @abstractmethod
    async def dispose(self) -> None: ...


class RelationalDatabase(AbstractDatabase):
    def __init__(self, name: str, url: str, echo: bool, bases: Sequence[type[DeclarativeBase]]) -> None:
        super().__init__(name, url, echo, bases)
        self._engine = create_engine(url, echo=echo)
        self._session_maker = sessionmaker(self._engine)

    @override
    async def create_all(self) -> None:
        for base in self._bases:
            base.metadata.create_all(self._engine)

    @override
    async def dispose(self) -> None:
        self._engine.dispose()


class AsyncRelationalDatabase(AbstractDatabase):
    def __init__(self, name: str, url: str, echo: bool, bases: Sequence[type[DeclarativeBase]]) -> None:
        super().__init__(name, url, echo, bases)
        self._engine = create_async_engine(url, echo=echo)
        self._session_maker = async_sessionmaker(self._engine)

    @override
    async def create_all(self) -> None:
        async with self._engine.begin() as connection:
            for base in self._bases:
                await connection.run_sync(base.metadata.create_all)

    @override
    async def dispose(self) -> None:
        await self._engine.dispose()
