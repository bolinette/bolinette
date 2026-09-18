from typing import Any, cast

from escondite import Cache
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.api import ApiController, autoroute
from bolinette.core import Bolinette
from bolinette.core.mapping import Mapper
from bolinette.data.relational import Service, declarative_base, service
from bolinette.web import controller
from tests.api.conftest import AppFactory


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class ItemResponse(BaseModel):
    id: int
    name: str


class ItemService(Service[Item]):
    pass


def _controller(cache: Cache) -> type[Any]:
    declarative_base("default", cache=cache)(Base)

    @controller("items", cache=cache)
    class ItemController(ApiController[Item]):
        @autoroute.get_all
        async def get_all(self) -> list[ItemResponse]: ...

    return ItemController


async def _require(blnt: Bolinette, ctrl_cls: type[Any]) -> ApiController[Item]:
    async with blnt.injector.get_scoped_injector() as scope:
        return cast(ApiController[Item], await scope.require(ctrl_cls))


class TestInjectedMembers:
    async def test_the_service_is_the_one_of_the_entity(self, make_app: AppFactory, cache: Cache) -> None:
        ctrl_cls = _controller(cache)
        blnt = await make_app()

        ctrl = await _require(blnt, ctrl_cls)

        assert isinstance(ctrl.service, Service)
        assert ctrl.service.entity is Item

    async def test_the_entity_comes_from_the_service(self, make_app: AppFactory, cache: Cache) -> None:
        ctrl_cls = _controller(cache)
        blnt = await make_app()

        assert (await _require(blnt, ctrl_cls)).entity is Item

    async def test_the_mapper_is_the_application_mapper(self, make_app: AppFactory, cache: Cache) -> None:
        ctrl_cls = _controller(cache)
        blnt = await make_app()

        ctrl = await _require(blnt, ctrl_cls)

        assert ctrl.mapper is await blnt.injector.require(Mapper)

    async def test_a_custom_service_is_injected(self, make_app: AppFactory, cache: Cache) -> None:
        ctrl_cls = _controller(cache)
        service(cache=cache)(ItemService)
        blnt = await make_app()

        assert isinstance((await _require(blnt, ctrl_cls)).service, ItemService)

    async def test_every_scope_builds_its_own_controller(self, make_app: AppFactory, cache: Cache) -> None:
        ctrl_cls = _controller(cache)
        blnt = await make_app()

        first = await _require(blnt, ctrl_cls)
        second = await _require(blnt, ctrl_cls)

        assert first is not second
        assert first.service is not second.service
