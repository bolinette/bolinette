from typing import Annotated, Any

import pytest
from escondite import Cache

from bolinette.core.mapping import BolinetteModel
from bolinette.web import AsgiApplication, Controller, PathParam, Payload, QueryParam, controller, get, post
from tests.web.conftest import AppFactory, AsgiClient


class ItemPayload(BolinetteModel):
    name: str
    count: int


class NestedPayload(BolinetteModel):
    label: str
    item: ItemPayload


async def _client(make_app: AppFactory) -> AsgiClient:
    blnt = await make_app()
    return AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())


class TestPathParam:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("42", "int:42"), ("1", "int:1")],
    )
    async def test_int_conversion(self, make_app: AppFactory, cache: Cache, raw: str, expected: str) -> None:
        @controller("p", cache=cache)
        class Ctrl(Controller):
            @get(r"int/{value:\d+}")
            async def as_int(self, value: Annotated[int, PathParam()]) -> str:
                return f"int:{value}"

        client = await _client(make_app)

        assert (await client.request("GET", f"/p/int/{raw}")).text == expected

    async def test_every_supported_type(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("p", cache=cache)
        class Ctrl(Controller):
            @get("float/{value}")
            async def as_float(self, value: Annotated[float, PathParam()]) -> str:
                return f"{value + 1}"

            @get("bool/{value}")
            async def as_bool(self, value: Annotated[bool, PathParam()]) -> str:
                return str(value)

            @get("str/{value}")
            async def as_str(self, value: Annotated[str, PathParam()]) -> str:
                return value

        client = await _client(make_app)

        assert (await client.request("GET", "/p/float/1.5")).text == "2.5"
        assert (await client.request("GET", "/p/bool/true")).text == "True"
        assert (await client.request("GET", "/p/bool/0")).text == "False"
        assert (await client.request("GET", "/p/str/abc")).text == "abc"

    async def test_unconvertible_value_is_a_bad_request(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("p", cache=cache)
        class Ctrl(Controller):
            @get("int/{value}")
            async def as_int(self, value: Annotated[int, PathParam()]) -> str:
                return str(value)

        client = await _client(make_app)
        result = await client.request("GET", "/p/int/abc")

        assert result.status == 400
        assert result.json()["errors"][0]["code"] == "web.route.param.wrong_type"

    async def test_unsupported_type_is_an_internal_error(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("p", cache=cache)
        class Ctrl(Controller):
            @get("obj/{value}")
            async def as_obj(self, value: Annotated[complex, PathParam()]) -> str:
                return str(value)

        client = await _client(make_app)

        assert (await client.request("GET", "/p/obj/1")).status == 500

    async def test_missing_key_uses_the_default(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("p", cache=cache)
        class Ctrl(Controller):
            @get("none")
            async def missing(self, other: Annotated[str, PathParam()] = "fallback") -> str:
                return other

        client = await _client(make_app)

        assert (await client.request("GET", "/p/none")).text == "fallback"

    async def test_missing_nullable_key_is_none(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("p", cache=cache)
        class Ctrl(Controller):
            @get("none")
            async def missing(self, other: Annotated[str | None, PathParam()]) -> str:
                return str(other)

        client = await _client(make_app)

        assert (await client.request("GET", "/p/none")).text == "None"

    async def test_missing_required_key_is_a_bad_request(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("p", cache=cache)
        class Ctrl(Controller):
            @get("none")
            async def missing(self, other: Annotated[str, PathParam()]) -> str:
                return other

        client = await _client(make_app)
        result = await client.request("GET", "/p/none")

        assert result.status == 400
        assert result.json()["errors"][0] == {
            "message": "Path parameter 'other' is missing",
            "code": "web.route.param.missing",
            "params": {"name": "other"},
        }


class TestQueryParam:
    async def test_single_value(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("q", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, name: Annotated[str, QueryParam()]) -> str:
                return name

        client = await _client(make_app)

        assert (await client.request("GET", "/q", query="name=bob")).text == "bob"

    async def test_last_value_wins(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("q", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, name: Annotated[str, QueryParam()]) -> str:
                return name

        client = await _client(make_app)

        assert (await client.request("GET", "/q", query="name=a&name=b")).text == "b"

    async def test_list_collects_every_value(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("q", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, ids: Annotated[list[int], QueryParam()]) -> str:
                return ",".join(str(i) for i in ids)

        client = await _client(make_app)

        assert (await client.request("GET", "/q", query="ids=1&ids=2")).text == "1,2"

    async def test_default_when_absent(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("q", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, name: Annotated[str, QueryParam()] = "anon") -> str:
                return name

        client = await _client(make_app)

        assert (await client.request("GET", "/q")).text == "anon"

    async def test_none_when_absent_and_nullable(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("q", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, name: Annotated[str | None, QueryParam()]) -> str:
                return str(name)

        client = await _client(make_app)

        assert (await client.request("GET", "/q")).text == "None"

    async def test_missing_required_value_is_a_bad_request(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("q", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, name: Annotated[str, QueryParam()]) -> str:
                return name

        client = await _client(make_app)
        result = await client.request("GET", "/q")

        assert result.status == 400
        assert result.json()["errors"][0]["code"] == "web.route.query.missing"

    async def test_blank_value_is_kept(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("q", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, name: Annotated[str, QueryParam()] = "anon") -> str:
                return f"[{name}]"

        client = await _client(make_app)

        assert (await client.request("GET", "/q", query="name=")).text == "[]"


class TestPayload:
    async def test_dict_body_is_mapped(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()]) -> str:
                return f"{payload.name}:{payload.count}"

        client = await _client(make_app)

        assert (await client.json_request("POST", "/b", {"name": "a", "count": 2})).text == "a:2"

    async def test_list_body_is_mapped(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[list[ItemPayload], Payload()]) -> str:
                return ",".join(p.name for p in payload)

        client = await _client(make_app)

        assert (await client.json_request("POST", "/b", [{"name": "a", "count": 1}])).text == "a"

    async def test_nested_body_is_mapped(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[NestedPayload, Payload()]) -> str:
                return payload.item.name

        client = await _client(make_app)
        body = {"label": "x", "item": {"name": "inner", "count": 1}}

        assert (await client.json_request("POST", "/b", body)).text == "inner"

    async def test_scalar_body_is_invalid(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()]) -> str:
                return payload.name

        client = await _client(make_app)
        result = await client.json_request("POST", "/b", 3)

        assert result.status == 400
        assert result.json()["errors"][0]["code"] == "payload.invalid"

    async def test_no_body_is_expected(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()]) -> str:
                return payload.name

        client = await _client(make_app)
        result = await client.request("POST", "/b")

        assert result.status == 400
        assert result.json()["errors"][0]["code"] == "payload.expected"

    async def test_no_body_with_a_nullable_annotation(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload | None, Payload()]) -> str:
                return str(payload)

        client = await _client(make_app)

        assert (await client.request("POST", "/b")).text == "None"

    async def test_no_body_with_a_default(self, make_app: AppFactory, cache: Cache) -> None:
        default = ItemPayload(name="default", count=0)

        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()] = default) -> str:
                return payload.name

        client = await _client(make_app)

        assert (await client.request("POST", "/b")).text == "default"

    async def test_missing_field_is_reported(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()]) -> str:
                return payload.name

        client = await _client(make_app)
        result = await client.json_request("POST", "/b", {"name": "a"})

        assert result.status == 400
        assert result.json()["errors"][0]["code"] == "payload.parameter.missing"
        assert result.json()["errors"][0]["params"] == {"path": "count"}

    async def test_wrong_field_type_is_reported(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()]) -> str:
                return payload.name

        client = await _client(make_app)
        result = await client.json_request("POST", "/b", {"name": "a", "count": "nope"})

        assert result.status == 400
        error = result.json()["errors"][0]
        assert error["code"] == "payload.parameter.wrong_type"
        assert "could not be converted to 'int'" in error["message"]

    async def test_null_field_is_reported(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()]) -> str:
                return payload.name

        client = await _client(make_app)
        result = await client.json_request("POST", "/b", {"name": None, "count": 1})

        assert result.status == 400
        assert result.json()["errors"][0]["code"] == "payload.parameter.not_nullable"

    async def test_every_field_error_is_reported(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()]) -> str:
                return payload.name

        client = await _client(make_app)
        result = await client.json_request("POST", "/b", {})

        assert sorted(e["params"]["path"] for e in result.json()["errors"]) == ["count", "name"]

    async def test_bad_json_is_treated_as_no_body(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload | None, Payload()]) -> str:
                return str(payload)

        client = await _client(make_app)

        assert (await client.request("POST", "/b", body=b"not json")).text == "None"

    async def test_chunked_body_is_reassembled(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("b", cache=cache)
        class Ctrl(Controller):
            @post("")
            async def create(self, payload: Annotated[ItemPayload, Payload()]) -> str:
                return payload.name

        client = await _client(make_app)
        chunks = [b'{"name": "chu', b'nked", "count": 1}']

        assert (await client.request("POST", "/b", chunks=chunks)).text == "chunked"


class TestUnannotatedParameters:
    async def test_plain_parameters_are_services(self, make_app: AppFactory, cache: Cache) -> None:
        class Service:
            value = "service"

        @controller("s", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, service: Service) -> str:
                return service.value

        blnt = await make_app()
        blnt.injector.services.add_scoped(Service)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        assert (await client.request("GET", "/s")).text == "service"

    async def test_an_unknown_parameter_is_an_internal_error(self, make_app: AppFactory, cache: Cache) -> None:
        class Unknown:
            pass

        @controller("s", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, unknown: Unknown) -> str:
                return "never"

        client = await _client(make_app)

        assert (await client.request("GET", "/s")).status == 500


class TestInjectedRequestState:
    async def test_request_and_response_data_are_injectable(self, make_app: AppFactory, cache: Cache) -> None:
        from bolinette.web import Request, ResponseData

        @controller("r", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, request: Request, data: ResponseData) -> dict[str, Any]:
                data.set_status(201)
                data.set_header("x-test", "yes")
                return {"path": request.path, "method": request.method}

        client = await _client(make_app)
        result = await client.request("GET", "/r")

        assert result.status == 201
        assert result.headers["x-test"] == "yes"
        assert result.json() == {"path": "/r", "method": "GET"}


class TestPayloadErrorTranslation:
    def _route(self) -> Any:
        from peritype import wrap_func, wrap_type

        from bolinette.web._routing import Route

        class Ctrl:
            def handler(self) -> None:
                pass

        return Route("POST", "/x", wrap_type(Ctrl), wrap_func(Ctrl.handler))

    def test_an_error_without_a_destination_is_an_invalid_payload(self) -> None:
        from peritype import wrap_type

        from bolinette.core.mapping.exceptions import NoProtocolError
        from bolinette.web._resources._resolvers import _transform_error  # pyright: ignore[reportPrivateUsage]

        error = _transform_error(NoProtocolError("nope"), wrap_type(ItemPayload), self._route())

        assert error.error_code == "payload.invalid"
        assert error.error_args == {"type": str(wrap_type(ItemPayload))}

    def test_an_unknown_mapping_error_is_an_invalid_payload(self) -> None:
        from peritype import wrap_type

        from bolinette.core.expressions import ExpressionTree
        from bolinette.core.mapping.exceptions import ImmutableFieldError
        from bolinette.web._resources._resolvers import _transform_error  # pyright: ignore[reportPrivateUsage]

        expr = ExpressionTree.new(ItemPayload).name
        error = _transform_error(ImmutableFieldError("nope", dest=expr), wrap_type(ItemPayload), self._route())

        assert error.error_code == "payload.invalid"

    def test_a_conversion_error_without_a_target_is_an_invalid_payload(self) -> None:
        from peritype import wrap_type

        from bolinette.core.expressions import ExpressionTree
        from bolinette.core.mapping.exceptions import ConversionError
        from bolinette.web._resources._resolvers import _transform_error  # pyright: ignore[reportPrivateUsage]

        expr = ExpressionTree.new(ItemPayload).name
        error = _transform_error(ConversionError("nope", dest=expr), wrap_type(ItemPayload), self._route())

        assert error.error_code == "payload.invalid"
