import pytest
from escondite import Cache
from pydantic import BaseModel
from soupape import ServiceCollection
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.api import ApiController, ApiExtension, autoroute
from bolinette.api.exceptions import ApiError
from bolinette.core import CoreExtension, meta
from bolinette.data import DataExtension
from bolinette.data.relational import declarative_base
from bolinette.web import Controller, WebExtension, controller, get
from bolinette.web._routing import RouteBucket
from tests.api.conftest import AppFactory, ClientFactory


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class OtherBase(DeclarativeBase):
    pass


class Orphan(OtherBase):
    __tablename__ = "orphans"

    id: Mapped[int] = mapped_column(primary_key=True)


class ItemResponse(BaseModel):
    id: int
    name: str


class TestExtension:
    def test_the_name_and_dependencies(self) -> None:
        assert ApiExtension.name == "api"
        assert list(ApiExtension.dependencies) == [CoreExtension, DataExtension, WebExtension]

    async def test_the_dependencies_are_loaded_first(self, make_app: AppFactory) -> None:
        blnt = await make_app()

        assert [type(ext) for ext in blnt.extensions] == [CoreExtension, WebExtension, DataExtension, ApiExtension]

    async def test_the_controller_is_a_scoped_service(self, make_app: AppFactory, cache: Cache) -> None:
        declarative_base("default", cache=cache)(Base)

        @controller("items", cache=cache)
        class ItemController(ApiController[Item]):
            @autoroute.get_all
            async def get_all(self) -> list[ItemResponse]: ...

        services = ServiceCollection()
        await make_app(services=services)

        assert services.is_registered(ItemController)


class TestAutorouteBuilding:
    async def test_the_stubs_become_routes(self, make_app: AppFactory, cache: Cache) -> None:
        declarative_base("default", cache=cache)(Base)

        @controller("items", cache=cache)
        class ItemController(ApiController[Item]):
            @autoroute.get_all
            async def get_all(self) -> list[ItemResponse]: ...

        await make_app()

        assert meta.has(ItemController.get_all, RouteBucket.KEY)

    async def test_a_controller_without_stubs_is_untouched(self, make_client: ClientFactory, cache: Cache) -> None:
        declarative_base("default", cache=cache)(Base)

        @controller("ping", cache=cache)
        class PingController(Controller):
            @get("")
            async def ping(self) -> str:
                return "pong"

        client = await make_client()

        assert (await client.get("/ping")).text == "pong"

    async def test_an_application_without_controllers(self, make_app: AppFactory) -> None:
        blnt = await make_app()

        assert [type(ext) for ext in blnt.extensions][-1] is ApiExtension

    async def test_a_stub_outside_an_api_controller_is_rejected(self, make_app: AppFactory, cache: Cache) -> None:
        declarative_base("default", cache=cache)(Base)

        @controller("items", cache=cache)
        class ItemController(Controller):
            @autoroute.get_all  # pyright: ignore[reportArgumentType]
            async def get_all(self) -> list[ItemResponse]: ...

        with pytest.raises(ApiError, match="Class must inherit from ApiController"):
            await make_app()

    async def test_an_entity_outside_the_registered_bases_is_rejected(self, make_app: AppFactory, cache: Cache) -> None:
        declarative_base("default", cache=cache)(Base)

        @controller("orphans", cache=cache)
        class OrphanController(ApiController[Orphan]):
            @autoroute.get_all
            async def get_all(self) -> list[ItemResponse]: ...

        with pytest.raises(ApiError, match="Entity is not a registered entity type"):
            await make_app()


class TestScaffolding:
    def test_the_hooks_are_declared_in_order(self) -> None:
        names = [hook.__name__ for hook in ApiExtension().get_new_project_hooks()]

        assert names == ["create_example_entity", "create_example_controller"]
