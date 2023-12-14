from collections.abc import Callable, Coroutine, Mapping, MutableMapping, Sequence
from typing import Any

from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import TypedReturnsRows

from bolinette.data.relational import DeclarativeBase

type _CoreSingleExecuteParams = Mapping[str, Any]
type _MutableCoreSingleExecuteParams = MutableMapping[str, Any]
type _CoreMultiExecuteParams = Sequence[_CoreSingleExecuteParams]
type _CoreAnyExecuteParams = _CoreMultiExecuteParams | _CoreSingleExecuteParams


class EntitySession[EntityT: DeclarativeBase]:
    def __init__(self, session: Session | AsyncSession) -> None:
        if isinstance(session, AsyncSession):
            self._session = (session, None)
            self.execute = session.execute
            self.add = session.add
            self.delete = session.delete
            self.commit = session.commit
            self.rollback = session.rollback
            self.close = session.close
        else:
            self._session = (None, session)
            self.execute = _to_async(session.execute)
            self.add = session.add
            self.delete = _to_async(session.delete)
            self.commit = _to_async(session.commit)
            self.rollback = _to_async(session.rollback)
            self.close = _to_async(session.close)

    async def execute(
        self,
        statement: TypedReturnsRows[tuple[EntityT]],
        params: _CoreAnyExecuteParams | None = None,
    ) -> Result[tuple[EntityT]]:
        match self._session:
            case (s, None):
                return await s.execute(statement, params)
            case (None, s):
                return s.execute(statement, params)

    def add(self, instance: EntityT) -> None:
        match self._session:
            case (s, None):
                return s.add(instance)
            case (None, s):
                return s.add(instance)

    async def delete(self, instance: EntityT) -> None:
        match self._session:
            case (s, None):
                return await s.delete(instance)
            case (None, s):
                return s.delete(instance)

    async def commit(self) -> None:
        match self._session:
            case (s, None):
                return await s.commit()
            case (None, s):
                return s.commit()

    async def rollback(self) -> None:
        match self._session:
            case (s, None):
                return await s.rollback()
            case (None, s):
                return s.rollback()

    async def close(self) -> None:
        match self._session:
            case (s, None):
                return await s.close()
            case (None, s):
                return s.close()


def _to_async[**P, T](func: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]:
    async def _call(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    return _call
