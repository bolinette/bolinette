# pyright: reportUnknownMemberType=false, reportInvalidTypeForm=false, reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false, reportArgumentType=false, reportUnknownArgumentType=false
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Concatenate

from sqlalchemy.orm import DeclarativeBase

from bolinette.api import ApiController
from bolinette.core.types import Function, Type
from bolinette.web import Payload, delete, get, patch, post, put


class _Autoroute:
    def get_all[DtoT](
        self,
        func: Callable[[Any], Awaitable[list[DtoT]]],
    ) -> Callable[[Any], Awaitable[list[DtoT]]]:
        func_f = Function(func)
        dto_t = func_f.return_type

        @get("")
        async def _inner(self: ApiController[DeclarativeBase]) -> list[dto_t.origin]:
            entity = await self.service.get_all()
            return self.mapper.map(list[self.cls], dto_t.origin, entity)

        return _inner

    def get_one[DtoT](
        self,
        func: Callable[[Any], Awaitable[DtoT]],
    ) -> Callable[[Any, str], Awaitable[DtoT]]:
        func_f = Function(func)
        dto_t = func_f.return_type

        @get(r"{id}")
        async def _inner(self: ApiController[DeclarativeBase], id: str) -> dto_t.origin:
            entity = await self.service.get_by_primary(id)
            return self.mapper.map(self.cls, dto_t.origin, entity)

        return _inner

    def create[PayloadT, DtoT](
        self,
        func: Callable[Concatenate[Any, PayloadT, ...], Awaitable[DtoT]],
    ) -> Callable[[Any, PayloadT], Awaitable[DtoT]]:
        func_f = Function(func)
        payload_t: Type[PayloadT] = func_f.anno_at(1)
        dto_t = func_f.return_type

        @post("")
        async def _inner(
            self: ApiController[DeclarativeBase],
            payload: Annotated[payload_t.origin, Payload],
        ) -> dto_t.origin:
            entity = self.service.create(payload)
            return self.mapper.map(self.cls, dto_t.origin, entity)

        return _inner

    def update[PayloadT, DtoT](
        self,
        func: Callable[Concatenate[Any, PayloadT, ...], Awaitable[DtoT]],
    ) -> Callable[[Any, str, PayloadT], Awaitable[DtoT]]:
        func_f = Function(func)
        payload_t: Type[PayloadT] = func_f.anno_at(1)
        dto_t = func_f.return_type

        @put(r"{id}")
        async def _inner(
            self: ApiController[DeclarativeBase],
            id: str,
            payload: Annotated[payload_t.origin, Payload],
        ) -> dto_t.origin:
            entity = await self.service.get_by_primary(id)
            entity = self.service.update(entity, payload)
            return self.mapper.map(self.cls, dto_t.origin, entity)

        return _inner

    def patch[PayloadT, DtoT](
        self,
        func: Callable[Concatenate[Any, PayloadT, ...], Awaitable[DtoT]],
    ) -> Callable[[Any, str, PayloadT], Awaitable[DtoT]]:
        func_f = Function(func)
        payload_t: Type[PayloadT] = func_f.anno_at(1)
        dto_t = func_f.return_type

        @patch(r"{id}")
        async def _inner(
            self: ApiController[DeclarativeBase],
            id: str,
            payload: Annotated[payload_t.origin, Payload],
        ) -> dto_t.origin:
            entity = await self.service.get_by_primary(id)
            entity = self.service.update(entity, payload)
            return self.mapper.map(self.cls, dto_t.origin, entity)

        return _inner

    def delete[DtoT](
        self,
        func: Callable[[Any], Awaitable[DtoT]],
    ) -> Callable[[Any, str], Awaitable[DtoT]]:
        func_f = Function(func)
        dto_t = func_f.return_type

        @delete(r"{id}")
        async def _inner(self: ApiController[DeclarativeBase], id: str) -> dto_t.origin:
            entity = await self.service.get_by_primary(id)
            await self.service.delete(entity)
            return self.mapper.map(self.cls, dto_t.origin, entity)

        return _inner


autoroute = _Autoroute()
