from types import TracebackType
from typing import Self

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase

from bolinette.core import Logger
from bolinette.data import relational
from bolinette.data.relational._session import EntitySession


class AsyncTransaction:
    def __init__(self, entities: "relational.EntityManager", logger: "Logger[AsyncTransaction]") -> None:
        self._entities = entities
        self._logger = logger
        self._sessions: dict[str, EntitySession[DeclarativeBase]] = {}

    def __contains__(self, name: str) -> bool:
        return name in self._sessions

    def get(self, name: str) -> EntitySession[DeclarativeBase]:
        if name not in self._sessions:
            self._sessions[name] = self._entities.get_engine_by_name(name).open_session()
            self._logger.debug(f"Opened session to database '{name}'")
        return self._sessions[name]

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                try:
                    await self.commit()
                    self._logger.debug("Applied changes to the databases")
                    return
                except SQLAlchemyError:
                    await self.rollback()
                    self._logger.error("Rolled back changes from the databases after a failed commit")
                    raise
            await self.rollback()
            self._logger.error("Rolled back changes from the databases")
        finally:
            await self.close()
            self._logger.debug("Closed sessions to the databases")

    async def commit(self) -> None:
        for session in self._sessions.values():
            await session.commit()

    async def rollback(self) -> None:
        for session in self._sessions.values():
            await session.rollback()

    async def close(self) -> None:
        for session in self._sessions.values():
            await session.close()
