from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import pytest
from escondite import Cache

from bolinette.core.mapping import BolinetteModel, Mapper
from bolinette.web import AsgiApplication, Controller, HttpHeaders, ResponseData, controller, get
from bolinette.web._json import to_json_value
from tests.web.conftest import AppFactory, AsgiClient


class Item(BolinetteModel):
    name: str
    count: int


@dataclass
class DcItem:
    name: str
    count: int


class Plain:
    name: str
    count: int

    def __init__(self, name: str, count: int) -> None:
        self.name = name
        self.count = count


async def _client(make_app: AppFactory) -> AsgiClient:
    blnt = await make_app()
    return AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())


class TestResponseData:
    def test_defaults(self) -> None:
        data = ResponseData()

        assert data.status is HTTPStatus.OK
        assert data.headers == {}

    def test_status_from_an_int(self) -> None:
        data = ResponseData()

        data.set_status(404)

        assert data.status is HTTPStatus.NOT_FOUND

    def test_status_from_an_enum(self) -> None:
        data = ResponseData()

        data.set_status(HTTPStatus.CREATED)

        assert data.status is HTTPStatus.CREATED

    def test_headers(self) -> None:
        data = ResponseData(headers={"a": "1"})

        data.set_header("b", "2")
        data.set_headers({"c": "3"})
        data.set_content_type("text/csv")

        assert data.has_header("a")
        assert data.get_header("b") == "2"
        assert data.get_header("missing", "fallback") == "fallback"
        assert data.headers[HttpHeaders.ContentType] == "text/csv"
        assert data.headers["c"] == "3"

    def test_unknown_header_without_a_default_raises(self) -> None:
        with pytest.raises(KeyError):
            ResponseData().get_header("missing")

    def test_headers_are_a_copy(self) -> None:
        data = ResponseData()

        data.headers["a"] = "1"

        assert data.headers == {}


class TestToJsonValue:
    @pytest.fixture
    async def mapper(self, make_app: AppFactory) -> Mapper:
        blnt = await make_app()
        return await blnt.injector.require(Mapper)

    @pytest.mark.parametrize("value", [None, True, False, 1, 1.5, "text"])
    def test_primitives_pass_through(self, mapper: Mapper, value: Any) -> None:
        assert to_json_value(mapper, value) == value

    def test_bytes_are_decoded(self, mapper: Mapper) -> None:
        assert to_json_value(mapper, b"raw") == "raw"

    def test_lists_and_tuples_recurse(self, mapper: Mapper) -> None:
        assert to_json_value(mapper, [b"a", ("b", 1)]) == ["a", ["b", 1]]

    def test_dicts_recurse_and_stringify_keys(self, mapper: Mapper) -> None:
        assert to_json_value(mapper, {1: b"a"}) == {"1": "a"}

    def test_models_go_through_the_mapper(self, mapper: Mapper) -> None:
        assert to_json_value(mapper, Item(name="a", count=1)) == {"name": "a", "count": 1}

    def test_dataclasses_go_through_the_mapper(self, mapper: Mapper) -> None:
        assert to_json_value(mapper, DcItem("a", 1)) == {"name": "a", "count": 1}

    def test_annotated_plain_objects_go_through_the_mapper(self, mapper: Mapper) -> None:
        assert to_json_value(mapper, Plain("a", 1)) == {"name": "a", "count": 1}

    def test_nested_containers(self, mapper: Mapper) -> None:
        assert to_json_value(mapper, {"items": [Item(name="a", count=1)]}) == {"items": [{"name": "a", "count": 1}]}


class TestSingleResults:
    async def test_none_is_an_empty_octet_stream(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> None:
                return None

        client = await _client(make_app)
        result = await client.request("GET", "/w")

        assert result.headers["content-type"] == "application/octet-stream"
        assert result.body == b""

    async def test_bytes_are_written_raw(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> bytes:
                return b"\x00\x01"

        client = await _client(make_app)
        result = await client.request("GET", "/w")

        assert result.headers["content-type"] == "application/octet-stream"
        assert result.body == b"\x00\x01"

    async def test_str_is_plain_text(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> str:
                return "hello"

        client = await _client(make_app)
        result = await client.request("GET", "/w")

        assert result.headers["content-type"] == "text/plain"
        assert result.text == "hello"

    @pytest.mark.parametrize(("returned", "expected"), [(3, "3"), (True, "true"), (1.5, "1.5")])
    async def test_scalars_are_json(self, make_app: AppFactory, cache: Cache, returned: Any, expected: str) -> None:
        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> Any:
                return returned

        client = await _client(make_app)
        result = await client.request("GET", "/w")

        assert result.headers["content-type"] == "application/json"
        assert result.text == expected

    async def test_dicts_lists_and_models_are_json(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("dict")
            async def as_dict(self) -> dict[str, Any]:
                return {"a": 1}

            @get("list")
            async def as_list(self) -> list[Any]:
                return [Item(name="a", count=1)]

            @get("model")
            async def as_model(self) -> Item:
                return Item(name="a", count=1)

        client = await _client(make_app)

        assert (await client.request("GET", "/w/dict")).json() == {"a": 1}
        assert (await client.request("GET", "/w/list")).json() == [{"name": "a", "count": 1}]
        assert (await client.request("GET", "/w/model")).json() == {"name": "a", "count": 1}

    async def test_a_custom_content_type_is_kept(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, data: ResponseData) -> str:
                data.set_content_type("text/csv")
                return "a,b"

        client = await _client(make_app)

        assert (await client.request("GET", "/w")).headers["content-type"] == "text/csv"


class TestUnpackedResults:
    async def test_a_sync_route_returning_a_coroutine(self, make_app: AppFactory, cache: Cache) -> None:
        async def inner() -> str:
            return "awaited"

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            def index(self) -> Any:
                return inner()

        client = await _client(make_app)

        assert (await client.request("GET", "/w")).text == "awaited"

    async def test_a_sync_generator_is_a_json_list(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> Iterator[Item]:
                return (Item(name=str(i), count=i) for i in range(2))

        client = await _client(make_app)
        result = await client.request("GET", "/w")

        assert result.headers["content-type"] == "application/json"
        assert result.json() == [{"name": "0", "count": 0}, {"name": "1", "count": 1}]

    async def test_an_async_generator_is_a_json_list(self, make_app: AppFactory, cache: Cache) -> None:
        async def gen() -> AsyncIterator[str]:
            yield "a"
            yield "b"

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> AsyncIterator[str]:
                return gen()

        client = await _client(make_app)

        assert (await client.request("GET", "/w")).text == "ab"

    async def test_an_empty_async_generator_is_an_empty_list(self, make_app: AppFactory, cache: Cache) -> None:
        async def gen() -> AsyncIterator[str]:
            return
            yield "never"

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> AsyncIterator[str]:
                return gen()

        client = await _client(make_app)
        result = await client.request("GET", "/w")

        assert result.headers["content-type"] == "application/json"
        assert result.body == b"[]"

    async def test_an_empty_sync_generator_is_an_empty_list(self, make_app: AppFactory, cache: Cache) -> None:
        def gen() -> Iterator[str]:
            return
            yield "never"

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> Iterator[str]:
                return gen()

        client = await _client(make_app)
        result = await client.request("GET", "/w")

        assert result.headers["content-type"] == "application/json"
        assert result.body == b"[]"

    async def test_a_non_generator_iterator_is_written_as_a_single_value(
        self, make_app: AppFactory, cache: Cache
    ) -> None:
        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> Any:
                return iter(())

        client = await _client(make_app)

        assert (await client.request("GET", "/w")).json() == {}

    async def test_a_callable_result_is_called_through_the_injector(self, make_app: AppFactory, cache: Cache) -> None:
        def later(mapper: Mapper) -> str:
            return "called"

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> Any:
                return later

        client = await _client(make_app)

        assert (await client.request("GET", "/w")).text == "called"

    async def test_a_coroutine_function_result_is_awaited(self, make_app: AppFactory, cache: Cache) -> None:
        async def later(mapper: Mapper) -> str:
            return "awaited"

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> Any:
                return later

        client = await _client(make_app)

        assert (await client.request("GET", "/w")).text == "awaited"

    async def test_an_async_generator_function_result_is_unpacked(self, make_app: AppFactory, cache: Cache) -> None:
        async def later(mapper: Mapper) -> AsyncIterator[str]:
            yield "x"

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> Any:
                return later

        client = await _client(make_app)

        assert (await client.request("GET", "/w")).text == "x"


class TestAwaitableResults:
    async def test_a_plain_awaitable_is_awaited(self, make_app: AppFactory, cache: Cache) -> None:
        import asyncio

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> Any:
                future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
                future.set_result("future")
                return future

        client = await _client(make_app)

        assert (await client.request("GET", "/w")).text == "future"
