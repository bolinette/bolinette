import inspect
from collections.abc import Callable
from datetime import datetime
from typing import Any, get_args, get_origin

import pytest
import sqlalchemy as sa
from peritype import wrap_type
from peritype.collections import TypeBag
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.api import ApiController, autoroute
from bolinette.api._autoroute import AutorouteKind, AutorouteMeta, build_autoroutes, controller_entity, iter_stubs
from bolinette.api.exceptions import ApiError
from bolinette.core import meta
from bolinette.web import PathParam, Payload
from bolinette.web._routing import RouteBucket


class OpaqueType(sa.types.UserDefinedType[Any]):
    def get_col_spec(self, **kwargs: Any) -> str:
        return "BLOB"


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class Pair(Base):
    __tablename__ = "pairs"

    left: Mapped[int] = mapped_column(primary_key=True)
    right: Mapped[str] = mapped_column(primary_key=True)


class Dated(Base):
    __tablename__ = "dated"

    at: Mapped[datetime] = mapped_column(primary_key=True)


class Opaque(Base):
    __tablename__ = "opaque"

    key: Mapped[Any] = mapped_column(OpaqueType(), primary_key=True)


class ItemPayload(BaseModel):
    name: str


class ItemResponse(BaseModel):
    id: int
    name: str


def _bag(*entities: type[Any]) -> TypeBag[Any]:
    bag = TypeBag[Any]()
    for entity in entities:
        bag.add(wrap_type(entity))
    return bag


def _bucket(func: Any) -> RouteBucket:
    return meta.get(func, RouteBucket.KEY)


def _route(ctrl_cls: type[Any], name: str) -> Any:
    return getattr(ctrl_cls, name)


def _props(ctrl_cls: type[Any], name: str) -> tuple[str, str]:
    bucket = _bucket(getattr(ctrl_cls, name))
    return bucket[0].method, bucket[0].path


def _annotation(ctrl_cls: type[Any], name: str, param: str) -> Any:
    return inspect.signature(getattr(ctrl_cls, name)).parameters[param].annotation


def _marker(annotation: Any) -> Any:
    return get_args(annotation)[1]


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
    async def patch(self, payload: ItemPayload) -> ItemResponse: ...

    @autoroute.delete
    async def delete(self) -> ItemResponse: ...


class PairController(ApiController[Pair]):
    @autoroute.get_one
    async def get_one(self) -> ItemResponse: ...

    @autoroute.update
    async def update(self, payload: ItemPayload) -> ItemResponse: ...


def _built_pair_controller() -> type[Any]:
    class Ctrl(ApiController[Pair]):
        @autoroute.get_one
        async def get_one(self) -> ItemResponse: ...

        @autoroute.update
        async def update(self, payload: ItemPayload) -> ItemResponse: ...

    build_autoroutes(Ctrl, _bag(Pair))
    return Ctrl


def _built_item_controller() -> type[Any]:
    class Ctrl(ApiController[Item]):
        @autoroute.get_all
        async def get_all(self) -> list[ItemResponse]: ...

        @autoroute.get_one
        async def get_one(self) -> ItemResponse: ...

        @autoroute.create
        async def create(self, payload: ItemPayload) -> ItemResponse: ...

        @autoroute.update
        async def update(self, payload: ItemPayload) -> ItemResponse: ...

        @autoroute.patch
        async def patch(self, payload: ItemPayload) -> ItemResponse: ...

        @autoroute.delete
        async def delete(self) -> ItemResponse: ...

    build_autoroutes(Ctrl, _bag(Item))
    return Ctrl


class TestStubDecorators:
    @pytest.mark.parametrize(
        ("decorator", "kind"),
        [
            (autoroute.get_all, "get_all"),
            (autoroute.get_one, "get_one"),
            (autoroute.create, "create"),
            (autoroute.update, "update"),
            (autoroute.patch, "patch"),
            (autoroute.delete, "delete"),
        ],
    )
    def test_each_decorator_marks_its_kind(self, decorator: Callable[..., Any], kind: AutorouteKind) -> None:
        async def stub(self: Any, *args: Any) -> None: ...

        marked = decorator(stub)
        stub_meta: AutorouteMeta = meta.get(marked, AutorouteMeta.KEY)

        assert marked is stub
        assert stub_meta.kind == kind


class TestIterStubs:
    def test_collects_the_marked_methods(self) -> None:
        assert {name: value[1].kind for name, value in iter_stubs(ItemController).items()} == {
            "get_all": "get_all",
            "get_one": "get_one",
            "create": "create",
            "update": "update",
            "patch": "patch",
            "delete": "delete",
        }

    def test_ignores_unmarked_and_non_callable_attributes(self) -> None:
        class Ctrl(ApiController[Item]):
            label = "ctrl"

            async def helper(self) -> None: ...

            @autoroute.get_all
            async def get_all(self) -> list[ItemResponse]: ...

        assert list(iter_stubs(Ctrl)) == ["get_all"]

    def test_finds_inherited_stubs(self) -> None:
        class Child(ItemController):
            pass

        assert set(iter_stubs(Child)) == set(iter_stubs(ItemController))

    def test_a_plain_class_has_no_stubs(self) -> None:
        class Ctrl:
            async def get_all(self) -> None: ...

        assert iter_stubs(Ctrl) == {}


class TestControllerEntity:
    def test_reads_the_generic_parameter(self) -> None:
        assert controller_entity(ItemController, _bag(Item)) is Item

    def test_requires_the_api_controller_base(self) -> None:
        class Ctrl:
            pass

        with pytest.raises(ApiError, match="Class must inherit from ApiController"):
            controller_entity(Ctrl, _bag(Item))

    def test_requires_a_registered_entity(self) -> None:
        with pytest.raises(ApiError, match="Entity is not a registered entity type"):
            controller_entity(ItemController, _bag(Pair))


class TestGeneratedRoutes:
    def test_the_stubs_are_replaced(self) -> None:
        ctrl_cls = _built_item_controller()

        assert _route(ctrl_cls, "get_all") is not ItemController.get_all
        assert all(meta.has(getattr(ctrl_cls, name), RouteBucket.KEY) for name in iter_stubs(ItemController))

    @pytest.mark.parametrize(
        ("name", "method", "path"),
        [
            ("get_all", "GET", ""),
            ("get_one", "GET", "{id}"),
            ("create", "POST", ""),
            ("update", "PUT", "{id}"),
            ("patch", "PATCH", "{id}"),
            ("delete", "DELETE", "{id}"),
        ],
    )
    def test_the_method_and_path_of_each_kind(self, name: str, method: str, path: str) -> None:
        assert _props(_built_item_controller(), name) == (method, path)

    def test_the_route_is_named_after_the_stub(self) -> None:
        ctrl_cls = _built_item_controller()

        route = _route(ctrl_cls, "get_one")

        assert route.__name__ == "get_one"
        assert route.__qualname__ == "_built_item_controller.<locals>.Ctrl.get_one"
        assert route.__module__ == __name__

    def test_the_stub_documentation_is_kept(self) -> None:
        class Ctrl(ApiController[Item]):
            @autoroute.get_all
            async def get_all(self) -> list[ItemResponse]: ...

        Ctrl.get_all.__doc__ = "every item"
        build_autoroutes(Ctrl, _bag(Item))

        assert _route(Ctrl, "get_all").__doc__ == "every item"

    def test_a_collection_route_takes_no_parameter(self) -> None:
        ctrl_cls = _built_item_controller()

        assert list(inspect.signature(_route(ctrl_cls, "get_all")).parameters) == ["self"]

    def test_the_primary_key_is_a_path_parameter(self) -> None:
        ctrl_cls = _built_item_controller()

        annotation = _annotation(ctrl_cls, "get_one", "id")

        assert list(inspect.signature(_route(ctrl_cls, "get_one")).parameters) == ["self", "id"]
        assert get_args(annotation)[0] is int
        assert isinstance(_marker(annotation), PathParam)

    def test_the_payload_keeps_the_stub_parameter_name(self) -> None:
        class Ctrl(ApiController[Item]):
            @autoroute.create
            async def create(self, body: ItemPayload) -> ItemResponse: ...

        build_autoroutes(Ctrl, _bag(Item))
        annotation = _annotation(Ctrl, "create", "body")

        assert get_args(annotation)[0] is ItemPayload
        assert isinstance(_marker(annotation), Payload)

    def test_an_update_takes_the_key_then_the_payload(self) -> None:
        ctrl_cls = _built_item_controller()

        assert list(inspect.signature(_route(ctrl_cls, "update")).parameters) == ["self", "id", "payload"]

    def test_the_return_type_comes_from_the_stub(self) -> None:
        ctrl_cls = _built_item_controller()

        signature = inspect.signature(_route(ctrl_cls, "get_all"))

        assert get_origin(signature.return_annotation) is list
        assert get_args(signature.return_annotation) == (ItemResponse,)
        assert _route(ctrl_cls, "get_one").__annotations__["return"] is ItemResponse

    def test_the_controller_is_the_self_annotation(self) -> None:
        ctrl_cls = _built_item_controller()

        assert inspect.signature(_route(ctrl_cls, "get_all")).parameters["self"].annotation is ctrl_cls


class TestCompositeKeys:
    def test_one_path_segment_per_column(self) -> None:
        ctrl_cls = _built_pair_controller()

        assert _props(ctrl_cls, "get_one") == ("GET", "{left}/{right}")
        assert _props(ctrl_cls, "update") == ("PUT", "{left}/{right}")

    def test_every_column_is_a_path_parameter(self) -> None:
        ctrl_cls = _built_pair_controller()

        assert list(inspect.signature(_route(ctrl_cls, "update")).parameters) == ["self", "left", "right", "payload"]
        assert get_args(_annotation(ctrl_cls, "get_one", "left"))[0] is int
        assert get_args(_annotation(ctrl_cls, "get_one", "right"))[0] is str


class TestInheritance:
    def test_an_indirect_subclass_keeps_the_entity(self) -> None:
        class Ctrl(PairController):
            pass

        build_autoroutes(Ctrl, _bag(Pair))

        assert _props(Ctrl, "get_one") == ("GET", "{left}/{right}")


class TestBuildFailures:
    def test_a_controller_without_stubs_is_left_alone(self) -> None:
        class Ctrl:
            async def get_all(self) -> None: ...

        build_autoroutes(Ctrl, _bag())

        assert not meta.has(Ctrl.get_all, RouteBucket.KEY)

    def test_a_stub_needs_a_return_type(self) -> None:
        class Ctrl(ApiController[Item]):
            @autoroute.get_all  # pyright: ignore[reportArgumentType]
            async def get_all(self): ...

        with pytest.raises(ApiError, match="Autoroute stub has no return type hint"):
            build_autoroutes(Ctrl, _bag(Item))

    def test_a_create_stub_needs_a_payload_parameter(self) -> None:
        class Ctrl(ApiController[Item]):
            @autoroute.create  # pyright: ignore[reportArgumentType]
            async def create(self) -> ItemResponse: ...

        with pytest.raises(ApiError, match="needs a payload parameter"):
            build_autoroutes(Ctrl, _bag(Item))

    def test_the_payload_parameter_needs_a_type_hint(self) -> None:
        class Ctrl(ApiController[Item]):
            @autoroute.update
            async def update(
                self,
                payload,  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            ) -> ItemResponse: ...

        with pytest.raises(ApiError, match="needs a payload parameter"):
            build_autoroutes(Ctrl, _bag(Item))

    def test_a_primary_key_must_be_a_scalar(self) -> None:
        class Ctrl(ApiController[Dated]):
            @autoroute.get_one
            async def get_one(self) -> ItemResponse: ...

        with pytest.raises(ApiError, match="cannot be a path parameter"):
            build_autoroutes(Ctrl, _bag(Dated))

    def test_a_primary_key_must_have_a_python_type(self) -> None:
        class Ctrl(ApiController[Opaque]):
            @autoroute.get_one
            async def get_one(self) -> ItemResponse: ...

        with pytest.raises(ApiError, match="has no python type"):
            build_autoroutes(Ctrl, _bag(Opaque))

    def test_an_entity_without_a_primary_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class Ctrl(ApiController[Item]):
            @autoroute.get_all
            async def get_all(self) -> list[ItemResponse]: ...

        monkeypatch.setattr(sa.inspect(Item), "primary_key", ())

        with pytest.raises(ApiError, match="Entity has no primary key"):
            build_autoroutes(Ctrl, _bag(Item))
