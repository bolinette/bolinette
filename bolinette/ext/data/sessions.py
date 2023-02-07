from typing import Any, Generic, TypeVar

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from bolinette import injectable
from bolinette.ext.data import Entity, __data_cache__

EntityT = TypeVar("EntityT", bound=Entity)


class ScopedSession(Generic[EntityT]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def execute(self, query: Any) -> sa.Result[Any]:
        return await self._session.execute(query)


@injectable(strategy="scoped", cache=__data_cache__)
class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ScopedSession[Any]] = {}

    def add(self, key: str, session: ScopedSession[Any]) -> None:
        self._sessions[key] = session

    def __contains__(self, key: str) -> bool:
        return key in self._sessions

    def get(self, key: str, *, hint: EntityT | None = None) -> ScopedSession[EntityT]:
        return self._sessions[key]

    async def commit(self) -> None:
        for session in self._sessions.values():
            await session.commit()

    async def rollback(self) -> None:
        for session in self._sessions.values():
            await session.rollback()
