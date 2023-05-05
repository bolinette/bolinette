from sqlalchemy.ext.asyncio import AsyncSession

from bolinette.injection import injectable
from bolinette.ext.data import __data_cache__


@injectable(strategy="scoped", cache=__data_cache__)
class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, AsyncSession] = {}

    def add(self, key: str, session: AsyncSession) -> None:
        self._sessions[key] = session

    def __contains__(self, key: str) -> bool:
        return key in self._sessions

    def get(self, key: str) -> AsyncSession:
        return self._sessions[key]

    async def commit(self) -> None:
        for session in self._sessions.values():
            await session.commit()

    async def rollback(self) -> None:
        for session in self._sessions.values():
            await session.rollback()
