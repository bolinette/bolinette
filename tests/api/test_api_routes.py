from collections.abc import Awaitable, Callable
from typing import Any

from escondite import Cache
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.api import ApiController, autoroute
from bolinette.core import meta
from bolinette.data.relational import declarative_base
from bolinette.web import controller, get, with_middleware
from bolinette.web._middleware import MiddlewareBag
from tests.api.conftest import AsgiClient, ClientFactory

CALLS: list[str] = []


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    price: Mapped[int | None]


class Pair(Base):
    __tablename__ = "pairs"

    left: Mapped[int] = mapped_column(primary_key=True)
    right: Mapped[str] = mapped_column(primary_key=True)
    label: Mapped[str]


class ItemPayload(BaseModel):
    name: str
    price: int | None = None


class ItemPatch(BaseModel):
    name: str | None = None
    price: int | None = None


class ItemResponse(BaseModel):
    id: int
    name: str
    price: int | None


class PairPayload(BaseModel):
    label: str


class PairResponse(BaseModel):
    left: int
    right: str
    label: str


def _items(cache: Cache) -> type[Any]:
    declarative_base("default", cache=cache)(Base)

    @controller("items", cache=cache)
    class ItemController(ApiController[Item]):
        @autoroute.get_all
        async def get_all(self) -> list[ItemResponse]: ...

        @autoroute.get_one
        async def get_one(self) -> ItemResponse: ...

        @autoroute.create
        async def create(self, payload: ItemPayload) -> ItemResponse: ...

        @autoroute.update
        async def update(self, payload: ItemPayload) -> ItemResponse: ...

        @autoroute.patch
        async def patch(self, payload: ItemPatch) -> ItemResponse: ...

        @autoroute.delete
        async def delete(self) -> ItemResponse: ...

    return ItemController


def _pairs(cache: Cache) -> type[Any]:
    declarative_base("default", cache=cache)(Base)

    @controller("pairs", cache=cache)
    class PairController(ApiController[Pair]):
        @autoroute.get_one
        async def get_one(self) -> PairResponse: ...

        @autoroute.update
        async def update(self, payload: PairPayload) -> PairResponse: ...

        @autoroute.delete
        async def delete(self) -> PairResponse: ...

    return PairController


class Tracer:
    def options(self) -> None:
        pass

    async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any:
        CALLS.append("in")
        result = await next()
        CALLS.append("out")
        return result


def _error_codes(result: Any) -> list[str]:
    return [error["code"] for error in result.json()["errors"]]


class TestGetAll:
    async def test_an_empty_collection(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.get("/items")

        assert result.status == 200
        assert result.json() == []

    async def test_every_entity_is_mapped_to_the_response_model(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client: AsgiClient = await make_client()
        await client.seed(Item(name="sword", price=10), Item(name="shield", price=None))

        result = await client.get("/items")

        assert result.json() == [
            {"id": 1, "name": "sword", "price": 10},
            {"id": 2, "name": "shield", "price": None},
        ]


class TestGetOne:
    async def test_the_primary_key_selects_the_entity(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10), Item(name="shield", price=None))

        result = await client.get("/items/2")

        assert result.json() == {"id": 2, "name": "shield", "price": None}

    async def test_an_unknown_key_is_a_not_found(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.get("/items/42")

        assert result.status == 404
        assert result.json()["errors"] == [
            {"message": "Item not found", "code": "api.entity.not_found", "params": {"entity": "Item", "id": 42}}
        ]

    async def test_a_key_of_the_wrong_type_is_a_bad_request(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.get("/items/abc")

        assert result.status == 400
        assert _error_codes(result) == ["web.route.param.wrong_type"]


class TestCreate:
    async def test_the_payload_is_stored_and_mapped_back(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.post("/items", {"name": "sword", "price": 10})

        assert result.status == 200
        assert result.json() == {"id": 1, "name": "sword", "price": 10}

    async def test_the_entity_is_flushed_before_the_response_is_mapped(
        self, make_client: ClientFactory, cache: Cache
    ) -> None:
        _items(cache)
        client = await make_client()

        created = await client.post("/items", {"name": "sword"})

        assert created.json()["id"] == 1
        assert (await client.get("/items")).json() == [{"id": 1, "name": "sword", "price": None}]

    async def test_a_missing_field_is_a_bad_request(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.post("/items", {"price": 10})

        assert result.status == 400
        assert _error_codes(result) == ["payload.parameter.missing"]

    async def test_a_missing_body_is_a_bad_request(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.post("/items")

        assert result.status == 400
        assert _error_codes(result) == ["payload.expected"]

    async def test_nothing_is_stored_when_the_payload_is_rejected(
        self, make_client: ClientFactory, cache: Cache
    ) -> None:
        _items(cache)
        client = await make_client()

        await client.post("/items", {"price": 10})

        assert (await client.get("/items")).json() == []


class TestUpdate:
    async def test_the_entity_is_merged_with_the_payload(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        result = await client.put("/items/1", {"name": "axe", "price": 20})

        assert result.json() == {"id": 1, "name": "axe", "price": 20}
        assert (await client.get("/items/1")).json() == {"id": 1, "name": "axe", "price": 20}

    async def test_a_field_left_out_of_the_payload_keeps_its_value(
        self, make_client: ClientFactory, cache: Cache
    ) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        result = await client.put("/items/1", {"name": "axe"})

        assert result.json() == {"id": 1, "name": "axe", "price": 10}

    async def test_an_unknown_key_is_a_not_found(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.put("/items/42", {"name": "axe"})

        assert result.status == 404
        assert _error_codes(result) == ["api.entity.not_found"]

    async def test_a_null_on_a_non_nullable_column_is_a_bad_request(
        self, make_client: ClientFactory, cache: Cache
    ) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        result = await client.put("/items/1", {"name": None})

        assert result.status == 400
        assert _error_codes(result) == ["payload.parameter.not_nullable"]


class TestPatch:
    async def test_only_the_given_fields_are_merged(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        result = await client.patch("/items/1", {"price": 20})

        assert result.json() == {"id": 1, "name": "sword", "price": 20}

    async def test_a_nullable_column_can_be_cleared(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        result = await client.patch("/items/1", {"price": None})

        assert result.json() == {"id": 1, "name": "sword", "price": None}

    async def test_an_empty_payload_changes_nothing(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        result = await client.patch("/items/1", {})

        assert result.json() == {"id": 1, "name": "sword", "price": 10}

    async def test_an_unknown_key_is_a_not_found(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.patch("/items/42", {"price": 20})

        assert result.status == 404
        assert _error_codes(result) == ["api.entity.not_found"]


class TestDelete:
    async def test_the_deleted_entity_is_returned(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        result = await client.delete("/items/1")

        assert result.json() == {"id": 1, "name": "sword", "price": 10}

    async def test_the_entity_is_gone(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        await client.delete("/items/1")

        assert (await client.get("/items")).json() == []

    async def test_an_unknown_key_is_a_not_found(self, make_client: ClientFactory, cache: Cache) -> None:
        _items(cache)
        client = await make_client()

        result = await client.delete("/items/42")

        assert result.status == 404
        assert _error_codes(result) == ["api.entity.not_found"]


class TestCompositeKeyRoutes:
    async def test_each_column_is_its_own_path_segment(self, make_client: ClientFactory, cache: Cache) -> None:
        _pairs(cache)
        client = await make_client()
        await client.seed(Pair(left=1, right="a", label="first"))

        result = await client.get("/pairs/1/a")

        assert result.json() == {"left": 1, "right": "a", "label": "first"}

    async def test_an_unknown_key_lists_every_column(self, make_client: ClientFactory, cache: Cache) -> None:
        _pairs(cache)
        client = await make_client()

        result = await client.get("/pairs/2/b")

        assert result.json()["errors"][0]["params"] == {"entity": "Pair", "left": 2, "right": "b"}

    async def test_an_update_reads_the_key_and_the_payload(self, make_client: ClientFactory, cache: Cache) -> None:
        _pairs(cache)
        client = await make_client()
        await client.seed(Pair(left=1, right="a", label="first"))

        result = await client.put("/pairs/1/a", {"label": "second"})

        assert result.json() == {"left": 1, "right": "a", "label": "second"}

    async def test_a_delete_removes_the_row(self, make_client: ClientFactory, cache: Cache) -> None:
        _pairs(cache)
        client = await make_client()
        await client.seed(Pair(left=1, right="a", label="first"))

        assert (await client.delete("/pairs/1/a")).status == 200
        assert (await client.get("/pairs/1/a")).status == 404


class TestHandWrittenRoutes:
    async def test_they_live_next_to_the_generated_ones(self, make_client: ClientFactory, cache: Cache) -> None:
        declarative_base("default", cache=cache)(Base)

        @controller("items", cache=cache)
        class ItemController(ApiController[Item]):
            @autoroute.get_all
            async def get_all(self) -> list[ItemResponse]: ...

            @get("count")
            async def count(self) -> int:
                return len(await self.service.get_all())

        client = await make_client()
        await client.seed(Item(name="sword", price=10))

        assert (await client.get("/items")).json() == [{"id": 1, "name": "sword", "price": 10}]
        assert (await client.get("/items/count")).json() == 1


class TestMiddlewares:
    async def test_a_controller_middleware_wraps_the_generated_routes(
        self, make_client: ClientFactory, cache: Cache
    ) -> None:
        CALLS.clear()
        declarative_base("default", cache=cache)(Base)

        @controller("items", cache=cache)
        @with_middleware(Tracer)
        class ItemController(ApiController[Item]):
            @autoroute.get_all
            async def get_all(self) -> list[ItemResponse]: ...

        client = await make_client()

        assert (await client.get("/items")).status == 200
        assert CALLS == ["in", "out"]

    async def test_the_middleware_bag_of_a_stub_is_kept(self, make_client: ClientFactory, cache: Cache) -> None:
        declarative_base("default", cache=cache)(Base)

        @controller("items", cache=cache)
        class ItemController(ApiController[Item]):
            @autoroute.get_all
            @with_middleware(Tracer)
            async def get_all(self) -> list[ItemResponse]: ...

        await make_client()

        assert meta.has(ItemController.get_all, MiddlewareBag.KEY)

    async def test_a_stub_middleware_runs(self, make_client: ClientFactory, cache: Cache) -> None:
        CALLS.clear()
        declarative_base("default", cache=cache)(Base)

        @controller("items", cache=cache)
        class ItemController(ApiController[Item]):
            @autoroute.get_all
            @with_middleware(Tracer)
            async def get_all(self) -> list[ItemResponse]: ...

        client = await make_client()

        assert (await client.get("/items")).status == 200
        assert CALLS == ["in", "out"]
