from collections.abc import Callable, Coroutine, Mapping, Sequence
from typing import Any

from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import TypedReturnsRows

from bolinette.data.relational import DeclarativeBase


class EntitySession[EntityT: DeclarativeBase]:
    def __init__(self, session: Session | AsyncSession) -> None:
        if isinstance(session, AsyncSession):
            self.execute = session.execute
            self.add = session.add
            self.delete = session.delete
            self.commit = session.commit
            self.rollback = session.rollback
            self.close = session.close
        else:
            self.execute = _to_async(session.execute)
            self.add = session.add
            self.delete = _to_async(session.delete)
            self.commit = _to_async(session.commit)
            self.rollback = _to_async(session.rollback)
            self.close = _to_async(session.close)

    async def execute(
        self,
        statement: TypedReturnsRows[tuple[EntityT]],
        params: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
    ) -> Result[tuple[EntityT]]: ...

    def add(self, instance: EntityT) -> None: ...

    async def delete(self, instance: EntityT) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def close(self) -> None: ...


def _to_async[**P, T](func: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]:
    async def _call(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    return _call
