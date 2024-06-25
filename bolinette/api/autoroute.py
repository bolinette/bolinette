from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from bolinette.api import ApiController
from bolinette.core.mapping.mapper import NoInitDestination
from bolinette.data.relational import DeclarativeBase
from bolinette.web import Payload, delete, get, patch, post, put


class _Autoroute:
    def get_all[
        ClsT: ApiController[DeclarativeBase],
        DtoT: NoInitDestination,
    ](
        self,
        dto_cls: type[DtoT],
    ) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any], Awaitable[list[DtoT]]]]:
        def decorator(
            func: Callable[[ClsT], Awaitable[None]],
        ) -> Callable[[ClsT], Awaitable[list[DtoT]]]:
            @get("")
            async def _inner(self: ClsT) -> list[dto_cls]:
                entity = await self.service.get_all()
                return self.mapper.map(list[self.cls], list[dto_cls], entity)

            return _inner

        return decorator

    def get_one[
        ClsT: ApiController[DeclarativeBase],
        DtoT: NoInitDestination,
    ](
        self,
        dto_cls: type[DtoT],
    ) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any, str], Awaitable[DtoT]]]:
        def decorator(
            func: Callable[[ClsT], Awaitable[None]],
        ) -> Callable[[ClsT, str], Awaitable[DtoT]]:
            @get(r"{id}")
            async def _inner(self: ClsT, id: str) -> dto_cls:
                entity = await self.service.get_by_primary(id)
                return self.mapper.map(self.cls, dto_cls, entity)

            return _inner

        return decorator

    def create[
        ClsT: ApiController[DeclarativeBase],
        PayloadT: NoInitDestination,
        DtoT: NoInitDestination,
    ](
        self,
        payload_cls: type[PayloadT],
        dto_cls: type[DtoT],
    ) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any, PayloadT], Awaitable[DtoT]]]:
        def decorator(
            func: Callable[[ClsT], Awaitable[None]],
        ) -> Callable[[ClsT, PayloadT], Awaitable[DtoT]]:
            @post("")
            async def _inner(self: ClsT, payload: Annotated[payload_cls, Payload]) -> dto_cls:
                entity = self.service.create(payload)
                return self.mapper.map(self.cls, dto_cls, entity)

            return _inner

        return decorator

    def update[
        ClsT: ApiController[DeclarativeBase],
        PayloadT: NoInitDestination,
        DtoT: NoInitDestination,
    ](
        self,
        payload_cls: type[PayloadT],
        dto_cls: type[DtoT],
    ) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any, str, PayloadT], Awaitable[DtoT]]]:
        def decorator(
            func: Callable[[ClsT], Awaitable[None]],
        ) -> Callable[[ClsT, str, PayloadT], Awaitable[DtoT]]:
            @put(r"{id}")
            async def _inner(self: ClsT, id: str, payload: Annotated[payload_cls, Payload]) -> dto_cls:
                entity = await self.service.get_by_primary(id)
                entity = self.service.update(entity, payload)
                return self.mapper.map(self.cls, dto_cls, entity)

            return _inner

        return decorator

    def patch[
        ClsT: ApiController[DeclarativeBase],
        PayloadT: NoInitDestination,
        DtoT: NoInitDestination,
    ](
        self,
        payload_cls: type[PayloadT],
        dto_cls: type[DtoT],
    ) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any, str, PayloadT], Awaitable[DtoT]]]:
        def decorator(
            func: Callable[[ClsT], Awaitable[None]],
        ) -> Callable[[ClsT, str, PayloadT], Awaitable[DtoT]]:
            @patch(r"{id}")
            async def _inner(self: ClsT, id: str, payload: Annotated[payload_cls, Payload]) -> dto_cls:
                entity = await self.service.get_by_primary(id)
                entity = self.service.update(entity, payload)
                return self.mapper.map(self.cls, dto_cls, entity)

            return _inner

        return decorator

    def delete[
        ClsT: ApiController[DeclarativeBase],
        DtoT: NoInitDestination,
    ](
        self,
        dto_cls: type[DtoT],
    ) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any, str], Awaitable[DtoT]]]:
        def decorator(
            func: Callable[[ClsT], Awaitable[None]],
        ) -> Callable[[ClsT, str], Awaitable[DtoT]]:
            @delete(r"{id}")
            async def _inner(self: ClsT, id: str) -> dto_cls:
                entity = await self.service.get_by_primary(id)
                await self.service.delete(entity)
                return self.mapper.map(self.cls, dto_cls, entity)

            return _inner

        return decorator


autoroute = _Autoroute()
