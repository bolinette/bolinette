import inspect
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, ClassVar, Literal, cast, get_type_hints

import sqlalchemy as sa
from peritype import TWrap, wrap_type
from peritype.collections import TypeBag
from sqlalchemy.orm import DeclarativeBase

from bolinette.api._controller import ApiController
from bolinette.api.exceptions import ApiError
from bolinette.core import meta
from bolinette.data.exceptions import EntityNotFoundError
from bolinette.web import PathParam, Payload, delete, get, patch, post, put
from bolinette.web.exceptions import NotFoundError

type AutorouteKind = Literal["get_all", "get_one", "create", "update", "patch", "delete"]

_API_CONTROLLER_TW = wrap_type(ApiController[Any])
_PATH_PARAM_TYPES: tuple[type[Any], ...] = (int, float, bool, str)


class AutorouteMeta:
    KEY: ClassVar[str] = "__blnt_api_autoroute_meta__"

    def __init__(self, kind: AutorouteKind) -> None:
        self.kind: AutorouteKind = kind


def _mark[FuncT: Callable[..., Any]](func: FuncT, kind: AutorouteKind) -> FuncT:
    meta.set(func, AutorouteMeta.KEY, AutorouteMeta(kind))
    return func


class _Autoroute:
    def get_all[CtrlT: ApiController[Any], DtoT](
        self,
        func: Callable[[CtrlT], Awaitable[list[DtoT]]],
        /,
    ) -> Callable[[CtrlT], Awaitable[list[DtoT]]]:
        return _mark(func, "get_all")

    def get_one[CtrlT: ApiController[Any], DtoT](
        self,
        func: Callable[[CtrlT], Awaitable[DtoT]],
        /,
    ) -> Callable[[CtrlT], Awaitable[DtoT]]:
        return _mark(func, "get_one")

    def create[CtrlT: ApiController[Any], PayloadT, DtoT](
        self,
        func: Callable[[CtrlT, PayloadT], Awaitable[DtoT]],
        /,
    ) -> Callable[[CtrlT, PayloadT], Awaitable[DtoT]]:
        return _mark(func, "create")

    def update[CtrlT: ApiController[Any], PayloadT, DtoT](
        self,
        func: Callable[[CtrlT, PayloadT], Awaitable[DtoT]],
        /,
    ) -> Callable[[CtrlT, PayloadT], Awaitable[DtoT]]:
        return _mark(func, "update")

    def patch[CtrlT: ApiController[Any], PayloadT, DtoT](
        self,
        func: Callable[[CtrlT, PayloadT], Awaitable[DtoT]],
        /,
    ) -> Callable[[CtrlT, PayloadT], Awaitable[DtoT]]:
        return _mark(func, "patch")

    def delete[CtrlT: ApiController[Any], DtoT](
        self,
        func: Callable[[CtrlT], Awaitable[DtoT]],
        /,
    ) -> Callable[[CtrlT], Awaitable[DtoT]]:
        return _mark(func, "delete")


autoroute = _Autoroute()


class _PrimaryKey:
    def __init__(self, entity: type[DeclarativeBase], controller: type[Any], route: str) -> None:
        self.columns: list[tuple[str, type[Any]]] = []
        for column in sa.inspect(entity).primary_key:
            try:
                python_type: type[Any] = column.type.python_type
            except NotImplementedError as err:
                raise ApiError(
                    f"Primary key column '{column.key}' has no python type",
                    controller=controller,
                    route=route,
                    entity=entity,
                ) from err
            if python_type not in _PATH_PARAM_TYPES:
                raise ApiError(
                    f"Primary key column '{column.key}' of type {python_type} cannot be a path parameter",
                    controller=controller,
                    route=route,
                    entity=entity,
                )
            self.columns.append((str(column.key), python_type))
        if not self.columns:
            raise ApiError("Entity has no primary key", controller=controller, route=route, entity=entity)

    @property
    def path(self) -> str:
        return "/".join(f"{{{name}}}" for name, _ in self.columns)

    def parameters(self) -> list[inspect.Parameter]:
        return [
            inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Annotated[cls, PathParam()])
            for name, cls in self.columns
        ]

    def values(self, kwargs: dict[str, Any]) -> list[Any]:
        return [kwargs[name] for name, _ in self.columns]


class _StubSpec:
    def __init__(self, controller: type[Any], name: str, stub: Callable[..., Any], kind: AutorouteKind) -> None:
        self.controller = controller
        self.name = name
        self.stub = stub
        self.kind: AutorouteKind = kind
        self.hints = get_type_hints(stub, include_extras=True)
        self.parameters = list(inspect.signature(stub).parameters.values())[1:]

    @property
    def return_type(self) -> Any:
        if "return" not in self.hints:
            raise ApiError("Autoroute stub has no return type hint", controller=self.controller, route=self.name)
        return self.hints["return"]

    @property
    def payload_type(self) -> Any:
        if not self.parameters or self.parameters[0].name not in self.hints:
            raise ApiError(
                "Autoroute stub needs a payload parameter with a type hint",
                controller=self.controller,
                route=self.name,
            )
        return self.hints[self.parameters[0].name]

    def parameter(self, annotation: Any) -> inspect.Parameter:
        return inspect.Parameter(
            self.parameters[0].name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=annotation
        )


class _RouteFactory:
    def __init__(self, entity: type[DeclarativeBase], spec: _StubSpec) -> None:
        self.entity = entity
        self.spec = spec
        self.primary_key = _PrimaryKey(entity, spec.controller, spec.name)

    def build(self) -> Callable[..., Any]:
        kind: AutorouteKind = self.spec.kind
        match kind:
            case "get_all":
                return self._finalize(self._get_all, get(""), [], self.spec.return_type)
            case "get_one":
                return self._finalize(
                    self._get_one, get(self.primary_key.path), self.primary_key.parameters(), self.spec.return_type
                )
            case "create":
                return self._finalize(self._create, post(""), [self._payload_parameter()], self.spec.return_type)
            case "update":
                return self._finalize(
                    self._update,
                    put(self.primary_key.path),
                    [*self.primary_key.parameters(), self._payload_parameter()],
                    self.spec.return_type,
                )
            case "patch":
                return self._finalize(
                    self._update,
                    patch(self.primary_key.path),
                    [*self.primary_key.parameters(), self._payload_parameter()],
                    self.spec.return_type,
                )
            case "delete":
                return self._finalize(
                    self._delete, delete(self.primary_key.path), self.primary_key.parameters(), self.spec.return_type
                )

    def _payload_parameter(self) -> inspect.Parameter:
        return self.spec.parameter(Annotated[self.spec.payload_type, Payload()])

    def _finalize(
        self,
        impl: Callable[..., Awaitable[Any]],
        decorator: Callable[[Callable[..., Any]], Callable[..., Any]],
        parameters: list[inspect.Parameter],
        return_type: Any,
    ) -> Callable[..., Any]:
        self_param = inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=self.spec.controller)
        signature = inspect.Signature([self_param, *parameters], return_annotation=return_type)

        async def route(self: ApiController[Any], *args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(self, *args, **kwargs).arguments
            del bound["self"]
            return await impl(self, bound)

        stub = self.spec.stub
        route.__name__ = self.spec.name
        route.__qualname__ = getattr(stub, "__qualname__", self.spec.name)
        route.__module__ = getattr(stub, "__module__", route.__module__)
        route.__doc__ = getattr(stub, "__doc__", None)
        route.__dict__.update(getattr(stub, "__dict__", {}))
        route.__signature__ = signature
        route.__annotations__ = {p.name: p.annotation for p in signature.parameters.values()} | {"return": return_type}
        return decorator(route)

    async def _get_entity(self, ctrl: ApiController[Any], kwargs: dict[str, Any]) -> Any:
        values = self.primary_key.values(kwargs)
        try:
            return await ctrl.service.get_by_primary(*values)
        except EntityNotFoundError as err:
            raise NotFoundError(
                f"{self.entity.__name__} not found",
                "api.entity.not_found",
                {"entity": self.entity.__name__, **{name: kwargs[name] for name, _ in self.primary_key.columns}},
            ) from err

    def _to_dto(self, ctrl: ApiController[Any], entity: Any) -> Any:
        return ctrl.mapper.map(self.entity, self.spec.return_type, entity)

    async def _get_all(self, ctrl: ApiController[Any], kwargs: dict[str, Any]) -> Any:
        del kwargs
        entities = await ctrl.service.get_all()
        return ctrl.mapper.map(list[self.entity], self.spec.return_type, entities)

    async def _get_one(self, ctrl: ApiController[Any], kwargs: dict[str, Any]) -> Any:
        return self._to_dto(ctrl, await self._get_entity(ctrl, kwargs))

    async def _create(self, ctrl: ApiController[Any], kwargs: dict[str, Any]) -> Any:
        entity = ctrl.service.create(kwargs[self.spec.parameters[0].name])
        await ctrl.service.repository.flush()
        return self._to_dto(ctrl, entity)

    async def _update(self, ctrl: ApiController[Any], kwargs: dict[str, Any]) -> Any:
        entity = await self._get_entity(ctrl, kwargs)
        ctrl.service.update(entity, kwargs[self.spec.parameters[0].name])
        await ctrl.service.repository.flush()
        return self._to_dto(ctrl, entity)

    async def _delete(self, ctrl: ApiController[Any], kwargs: dict[str, Any]) -> Any:
        entity = await self._get_entity(ctrl, kwargs)
        await ctrl.service.delete(entity)
        return self._to_dto(ctrl, entity)


def controller_entity(ctrl_cls: type[Any], entities: TypeBag[Any]) -> type[DeclarativeBase]:
    ctrl_tw = wrap_type(ctrl_cls)
    base_tw = next((b for b in ctrl_tw.iter_bases() if b.matches(_API_CONTROLLER_TW)), None)
    if base_tw is None:
        raise ApiError("Class must inherit from ApiController[Entity]", controller=ctrl_cls)
    entity_tw: TWrap[Any] = base_tw.generic_params[0]
    if entity_tw not in entities:
        raise ApiError("Entity is not a registered entity type", controller=ctrl_cls, entity=entity_tw.origin)
    return cast(type[DeclarativeBase], entity_tw.origin)


def iter_stubs(ctrl_cls: type[Any]) -> dict[str, tuple[Callable[..., Any], AutorouteMeta]]:
    stubs: dict[str, tuple[Callable[..., Any], AutorouteMeta]] = {}
    for name in dir(ctrl_cls):
        attr: Any = inspect.getattr_static(ctrl_cls, name, None)
        if callable(attr) and meta.has(attr, AutorouteMeta.KEY):
            stubs[name] = (attr, meta.get(attr, AutorouteMeta.KEY))
    return stubs


def build_autoroutes(ctrl_cls: type[Any], entities: TypeBag[Any]) -> None:
    stubs = iter_stubs(ctrl_cls)
    if not stubs:
        return
    entity = controller_entity(ctrl_cls, entities)
    for name, (stub, stub_meta) in stubs.items():
        route = _RouteFactory(entity, _StubSpec(ctrl_cls, name, stub, stub_meta.kind)).build()
        setattr(ctrl_cls, name, route)
