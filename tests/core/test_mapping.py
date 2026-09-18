"""The core extension's Mapper: registration as a service and cache-based discovery."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, override

from escondite import Cache
from muotti import ABSENT, FieldSpec, Mapper, Maybe, ObjectProtocol, Profile, mapping, mapping_protocol
from peritype import TWrap, wrap_type

from bolinette.core import startup
from tests.core.conftest import AppFactory


@dataclass
class AddressDC:
    city: str


@dataclass
class PersonDC:
    name: str
    age: int
    address: AddressDC | None = None
    tags: list[str] = field(default_factory=list[str])


class TestMapperInApp:
    async def test_mapper_is_a_core_service(self, make_app: AppFactory, cache: Cache) -> None:
        """The core extension registers a `Mapper` with the built-in protocols."""
        seen: list[Mapper] = []

        @startup(cache=cache)
        async def init(mapper: Mapper) -> None:
            seen.append(mapper)

        blnt = await make_app()
        await blnt.startup()

        assert seen[0].map(dict[str, Any], PersonDC, {"name": "Bob", "age": 3}) == PersonDC("Bob", 3)

    async def test_decorated_profiles_are_loaded(self, make_app: AppFactory, cache: Cache) -> None:
        """Profiles decorated with `mapping` are loaded into the application mapper."""

        @dataclass
        class Dest:
            name: str
            role: str

        @mapping(cache=cache)
        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(lambda d: d.role, lambda o: o.default(lambda: "guest"))

        seen: list[Mapper] = []

        @startup(cache=cache)
        async def init(mapper: Mapper) -> None:
            seen.append(mapper)

        blnt = await make_app()
        await blnt.startup()

        assert seen[0].map(PersonDC, Dest, PersonDC("Bob", 3)) == Dest("Bob", "guest")

    async def test_decorated_protocols_are_loaded(self, make_app: AppFactory, cache: Cache) -> None:
        """Protocols decorated with `mapping_protocol` are registered in the application mapper."""

        class Marker:
            pass

        @mapping_protocol(cache=cache)
        class MarkerProtocol(ObjectProtocol):
            priority = 500

            @override
            def matches(self, t: TWrap[Any]) -> bool:
                return bool(t.match(Marker))

            @override
            def fields(self, t: TWrap[Any]) -> Mapping[str, FieldSpec]:
                return {}

            @override
            def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
                return ABSENT

            @override
            def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
                return Marker()

        seen: list[Mapper] = []

        @startup(cache=cache)
        async def init(mapper: Mapper) -> None:
            seen.append(mapper)

        blnt = await make_app()
        await blnt.startup()

        assert isinstance(seen[0].registry.resolve(wrap_type(Marker)), MarkerProtocol)
