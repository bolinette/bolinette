from typing import Any, Self

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class RelationalSession:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> Self:
        await self._session.__aenter__()
        return self

    async def __aexit__(self, type_: Any, value: Any, traceback: Any) -> None:
        await self._session.__aexit__(type_, value, traceback)


class RelationalDatabase:
    def __init__(self, uri: str, echo: bool):
        self._engine = create_async_engine(uri, echo=echo)
        self._session_maker = async_sessionmaker(self._engine)
        self._metadata = MetaData()

    @property
    def metadata(self) -> MetaData:
        return self._metadata

    def get_session(self) -> AsyncSession:
        return self._session_maker()
