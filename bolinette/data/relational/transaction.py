from types import TracebackType
from typing import Self

from sqlalchemy.exc import SQLAlchemyError

from bolinette.core import Logger
from bolinette.core.injection import init_method
from bolinette.data import relational
from bolinette.data.relational import DeclarativeBase, EntitySession


class AsyncTransaction:
    def __init__(self, entities: "relational.EntityManager", logger: "Logger[AsyncTransaction]") -> None:
        self._entities = entities
        self._logger = logger
        self._sessions: dict[str, EntitySession[DeclarativeBase]] = {}

    def add(self, key: str, session: EntitySession[DeclarativeBase]) -> None:
        self._sessions[key] = session

    def __contains__(self, key: str) -> bool:
        return key in self._sessions

    def get(self, key: str) -> EntitySession[DeclarativeBase]:
        return self._sessions[key]

    @init_method
    def open_sessions(self) -> None:
        for engine in self._entities.engines.values():
            engine.open_session(self)
        self._logger.debug("Opened sessions to the database")

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, *args: tuple[type[BaseException], Exception, TracebackType] | tuple[None, None, None]
    ) -> None:
        rollback = False
        if args == (None, None, None):
            try:
                for session in self._sessions.values():
                    await session.commit()
                self._logger.debug("Applying changes to the database")
            except SQLAlchemyError:
                rollback = True
        else:
            rollback = True
        if rollback:
            for session in self._sessions.values():
                await session.rollback()
            self._logger.error("Rolling back changes from the database")
        for session in self._sessions.values():
            await session.close()
        self._logger.debug("Closed sessions to the database")

    async def commit(self) -> None:
        for session in self._sessions.values():
            await session.commit()

    async def rollback(self) -> None:
        for session in self._sessions.values():
            await session.rollback()

    async def close(self) -> None:
        for session in self._sessions.values():
            await session.close()
