"""Object mapping: protocols, field decisions, conversions, merging and mapping profiles."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, NotRequired, TypedDict, cast, override

import pytest
from escondite import Cache
from peritype import TWrap, wrap_type
from pydantic import BaseModel

from bolinette.core import startup
from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping import (
    ABSENT,
    DataclassProtocol,
    FieldOverride,
    FieldSpec,
    MapMode,
    Mapper,
    MappingProtocol,
    ObjectProtocol,
    PlainObjectProtocol,
    Profile,
    ProtocolRegistry,
    PydanticProtocol,
    SequenceProtocol,
    SetProtocol,
    TypedDictProtocol,
    is_present,
    mapping,
    mapping_protocol,
)
from bolinette.core.mapping._absence import Maybe
from bolinette.core.mapping._decision import Action, decide
from bolinette.core.mapping._paths import read_expr
from bolinette.core.mapping._spec import NO_OVERRIDE
from bolinette.core.mapping._utils import dict_value_type, element_type, is_value_type
from bolinette.core.mapping.exceptions import (
    ConversionError,
    DestinationNotNullableError,
    InstantiationError,
    MappingConfigurationError,
    NoProtocolError,
    SourceNotFoundError,
    ValidationError,
)
from tests.core.conftest import AppFactory


@dataclass
class AddressDC:
    city: str
    zip_code: str | None = None


@dataclass
class PersonDC:
    name: str
    age: int
    address: AddressDC | None = None
    tags: list[str] = field(default_factory=list[str])


@dataclass
class PersonWithAddressesDC:
    name: str
    addresses: list[AddressDC] = field(default_factory=list[AddressDC])


class AddressModel(BaseModel):
    city: str
    zip_code: str | None = None


class PersonModel(BaseModel):
    name: str
    age: int
    address: AddressModel | None = None
    tags: list[str] = []


class PersonDict(TypedDict):
    name: str
    age: int
    nickname: NotRequired[str]


class PlainPerson:
    name: str
    age: int
    role: str = "user"

    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age


class PlainWithoutInit:
    name: str
    age: int


@pytest.fixture
def mapper() -> Mapper:
    """A mapper with the seven built-in protocols and no profile."""
    instance = Mapper()
    for protocol in (
        PydanticProtocol(),
        TypedDictProtocol(),
        DataclassProtocol(),
        MappingProtocol(),
        SequenceProtocol(),
        SetProtocol(),
        PlainObjectProtocol(),
    ):
        instance.add_protocol(protocol)
    return instance


class TestAbsence:
    def test_absent_is_a_falsy_singleton(self) -> None:
        """`ABSENT` is unique, falsy and prints as its name."""
        assert type(ABSENT)() is ABSENT
        assert not ABSENT
        assert repr(ABSENT) == "ABSENT"

    def test_is_present(self) -> None:
        """`is_present` is false for `ABSENT` only, `None` counts as present."""
        assert not is_present(ABSENT)
        assert is_present(None)
        assert is_present(0)


class TestProtocolRegistry:
    def test_resolution_by_priority(self, mapper: Mapper) -> None:
        """Each built-in protocol claims the kind of type it was made for."""
        registry = mapper.registry

        assert isinstance(registry.resolve(wrap_type(PersonModel)), PydanticProtocol)
        assert isinstance(registry.resolve(wrap_type(PersonDict)), TypedDictProtocol)
        assert isinstance(registry.resolve(wrap_type(PersonDC)), DataclassProtocol)
        assert isinstance(registry.resolve(wrap_type(dict[str, Any])), MappingProtocol)
        assert isinstance(registry.resolve(wrap_type(PlainPerson)), PlainObjectProtocol)

    def test_union_has_no_protocol(self, mapper: Mapper) -> None:
        """A union of several classes matches no protocol."""
        assert mapper.registry.resolve(wrap_type(int | str)) is None

    def test_nullable_type_uses_the_inner_class(self, mapper: Mapper) -> None:
        """An optional type is resolved through its non-null member."""
        assert isinstance(mapper.registry.resolve(wrap_type(PersonDC | None)), DataclassProtocol)

    def test_custom_protocol_priority(self) -> None:
        """A protocol with a higher priority is tried first."""

        class Everything(ObjectProtocol):
            priority = 1000

            @override
            def matches(self, t: TWrap[Any]) -> bool:
                return True

            @override
            def fields(self, t: TWrap[Any]) -> Mapping[str, FieldSpec]:
                return {}

            @override
            def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
                return ABSENT

            @override
            def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
                return None

        registry = ProtocolRegistry()
        registry.register(DataclassProtocol())
        registry.register(Everything())

        assert isinstance(registry.resolve(wrap_type(PersonDC)), Everything)


class TestProtocolFields:
    def test_dataclass_fields(self) -> None:
        """Dataclass fields report nullability and default presence."""
        specs = DataclassProtocol().fields(wrap_type(PersonDC))

        assert set(specs) == {"name", "age", "address", "tags"}
        assert not specs["name"].has_default
        assert specs["address"].nullable
        assert specs["address"].has_default
        assert specs["tags"].has_default

    def test_pydantic_fields(self) -> None:
        """Pydantic fields report default presence from the field info."""
        specs = PydanticProtocol().fields(wrap_type(PersonModel))

        assert not specs["age"].has_default
        assert specs["tags"].has_default
        assert specs["address"].nullable

    def test_pydantic_read_field_skips_unset(self) -> None:
        """Only fields explicitly set on a model are read, defaults are `ABSENT`."""
        specs = PydanticProtocol().fields(wrap_type(PersonModel))
        model = PersonModel(name="Bob", age=3)

        assert PydanticProtocol().read_field(model, specs["name"]) == "Bob"
        assert PydanticProtocol().read_field(model, specs["tags"]) is ABSENT

    def test_typed_dict_fields(self) -> None:
        """Optional keys of a `TypedDict` count as having a default."""
        specs = TypedDictProtocol().fields(wrap_type(PersonDict))

        assert not specs["name"].has_default
        assert specs["nickname"].has_default

    def test_plain_object_fields(self) -> None:
        """Plain classes expose their annotated attributes, class values count as defaults."""
        specs = PlainObjectProtocol().fields(wrap_type(PlainPerson))

        assert set(specs) == {"name", "age", "role"}
        assert not specs["name"].has_default
        assert specs["role"].has_default

    def test_mapping_has_no_fields(self) -> None:
        """A plain `dict` has no declared fields and says so through `knows_fields`."""
        assert MappingProtocol().fields(wrap_type(dict[str, Any])) == {}
        assert not MappingProtocol().knows_fields
        assert DataclassProtocol().knows_fields


class TestMapSignature:
    def test_source_class_defaults_to_the_source_type(self, mapper: Mapper) -> None:
        """`map(dest_cls, src)` uses `type(src)` as the source class."""
        assert mapper.map(PersonModel, PersonDC("Bob", 3)) == PersonModel(name="Bob", age=3)

    def test_explicit_source_class(self, mapper: Mapper) -> None:
        """`map(src_cls, dest_cls, src)` is needed when `type(src)` is not the intended class, like a dict."""
        assert mapper.map(dict[str, Any], PersonDC, {"name": "Bob", "age": 3}) == PersonDC("Bob", 3)

    def test_merge_short_form(self, mapper: Mapper) -> None:
        """`merge(src, dest)` uses `type(src)` as the source class."""
        dest = PersonDC("Ann", 1)

        assert mapper.merge(PersonDC("Bob", 3), dest) is dest
        assert dest.name == "Bob"

    def test_wrong_arity_raises(self, mapper: Mapper) -> None:
        """Any other number of positional arguments is a programming error."""
        with pytest.raises(TypeError):
            mapper.map(PersonDC)  # pyright: ignore[reportCallIssue]
        with pytest.raises(TypeError):
            mapper.merge(PersonDC("Bob", 3))  # pyright: ignore[reportCallIssue]


class TestCreate:
    def test_dataclass_to_dataclass(self, mapper: Mapper) -> None:
        """Fields with the same name are copied into a new instance."""
        result = mapper.map(PersonDC, PersonDC, PersonDC("Bob", 3, tags=["a"]))

        assert result == PersonDC("Bob", 3, tags=["a"])

    def test_dict_to_dataclass(self, mapper: Mapper) -> None:
        """A plain dictionary is a valid source for any destination."""
        result = mapper.map(dict[str, Any], PersonDC, {"name": "Bob", "age": 3})

        assert result == PersonDC("Bob", 3)

    def test_dataclass_to_pydantic(self, mapper: Mapper) -> None:
        """A dataclass maps to a pydantic model, nested objects included."""
        result = mapper.map(PersonDC, PersonModel, PersonDC("Bob", 3, AddressDC("Paris")))

        assert result == PersonModel(name="Bob", age=3, address=AddressModel(city="Paris"))

    def test_pydantic_to_typed_dict(self, mapper: Mapper) -> None:
        """A `TypedDict` destination is built as a dictionary."""
        result = mapper.map(PersonModel, PersonDict, PersonModel(name="Bob", age=3))

        assert result == {"name": "Bob", "age": 3}

    def test_to_plain_object(self, mapper: Mapper) -> None:
        """A plain class is instantiated through its constructor and extra fields are set."""
        result = mapper.map(dict[str, Any], PlainPerson, {"name": "Bob", "age": 3, "role": "admin"})

        assert (result.name, result.age, result.role) == ("Bob", 3, "admin")

    def test_to_plain_object_without_init(self, mapper: Mapper) -> None:
        """A plain class without constructor gets its attributes assigned."""
        result = mapper.map(dict[str, Any], PlainWithoutInit, {"name": "Bob", "age": 3})

        assert (result.name, result.age) == ("Bob", 3)

    def test_values_are_converted(self, mapper: Mapper) -> None:
        """Values are coerced to the destination field type."""
        result = mapper.map(dict[str, Any], PersonDC, {"name": "Bob", "age": "3"})

        assert result.age == 3

    def test_conversion_failure_raises(self, mapper: Mapper) -> None:
        """A value that cannot be coerced raises a `ConversionError` with both paths."""
        with pytest.raises(ConversionError, match=r"Destination path 'PersonDC\.age'.*From source path") as info:
            mapper.map(dict[str, Any], PersonDC, {"name": "Bob", "age": "old"})

        assert str(info.value.dest) == "PersonDC.age"

    def test_missing_source_raises(self, mapper: Mapper) -> None:
        """A required destination field with no source and no default is an error."""
        with pytest.raises(SourceNotFoundError, match="source path not found"):
            mapper.map(dict[str, Any], PersonDC, {"name": "Bob"})

    def test_missing_source_uses_default(self, mapper: Mapper) -> None:
        """A destination field with a default is left to the constructor when the source lacks it."""
        result = mapper.map(dict[str, Any], PlainPerson, {"name": "Bob", "age": 3})

        assert result.role == "user"

    def test_missing_source_nullable_becomes_none(self, mapper: Mapper) -> None:
        """A nullable destination field without default is set to `None` when the source lacks it."""

        @dataclass
        class Dest:
            value: int | None

        result = mapper.map(dict[str, Any], Dest, {})

        assert result.value is None

    def test_none_to_non_nullable_raises(self, mapper: Mapper) -> None:
        """A `None` source value cannot be bound to a non-nullable field."""
        with pytest.raises(DestinationNotNullableError):
            mapper.map(dict[str, Any], PersonDC, {"name": None, "age": 3})

    def test_none_to_nullable(self, mapper: Mapper) -> None:
        """A `None` source value is assigned to a nullable field."""
        result = mapper.map(dict[str, Any], AddressDC, {"city": "Paris", "zip_code": None})

        assert result.zip_code is None

    def test_pydantic_defaults_are_not_copied(self, mapper: Mapper) -> None:
        """Unset pydantic fields are absent, so the destination keeps its own default."""

        @dataclass
        class Dest:
            name: str
            tags: list[str] = field(default_factory=lambda: ["default"])

        result = mapper.map(PersonModel, Dest, PersonModel(name="Bob", age=3))

        assert result.tags == ["default"]

    def test_no_protocol_for_destination_raises(self, mapper: Mapper) -> None:
        """A destination type no protocol handles is an error."""
        with pytest.raises(NoProtocolError):
            mapper.map(dict[str, Any], int | str, {})  # pyright: ignore[reportArgumentType]

    def test_instantiation_failure_raises(self, mapper: Mapper) -> None:
        """A constructor that fails is wrapped into an `InstantiationError`."""

        @dataclass
        class Picky:
            value: int

            def __post_init__(self) -> None:
                raise ValueError("nope")

        with pytest.raises(InstantiationError):
            mapper.map(dict[str, Any], Picky, {"value": 1})


class TestNested:
    def test_nested_object(self, mapper: Mapper) -> None:
        """Nested structures are mapped recursively."""
        result = mapper.map(dict[str, Any], PersonDC, {"name": "Bob", "age": 3, "address": {"city": "Paris"}})

        assert result.address == AddressDC("Paris")

    def test_nested_none(self, mapper: Mapper) -> None:
        """A `None` nested value is kept as `None`."""
        result = mapper.map(dict[str, Any], PersonDC, {"name": "Bob", "age": 3, "address": None})

        assert result.address is None

    def test_list_of_scalars_is_converted(self, mapper: Mapper) -> None:
        """Items of a scalar list are converted to the item type."""

        @dataclass
        class Dest:
            ids: list[int]

        result = mapper.map(dict[str, Any], Dest, {"ids": ["1", "2"]})

        assert result.ids == [1, 2]

    def test_list_of_objects(self, mapper: Mapper) -> None:
        """Items of a structured list are mapped one by one."""
        result = mapper.map(
            dict[str, Any],
            PersonWithAddressesDC,
            {"name": "Bob", "addresses": [{"city": "Paris"}, {"city": "Lyon"}]},
        )

        assert result.addresses == [AddressDC("Paris"), AddressDC("Lyon")]

    def test_non_iterable_for_list_raises(self, mapper: Mapper) -> None:
        """A scalar where a list of objects is expected is a conversion error."""
        with pytest.raises(ConversionError, match="expected an iterable"):
            mapper.map(dict[str, Any], PersonWithAddressesDC, {"name": "Bob", "addresses": "Paris"})

    def test_nested_error_path(self, mapper: Mapper) -> None:
        """Errors inside nested items carry the full destination path."""
        with pytest.raises(SourceNotFoundError) as info:
            mapper.map(dict[str, Any], PersonWithAddressesDC, {"name": "Bob", "addresses": [{}]})

        assert str(info.value.dest) == "PersonWithAddressesDC.addresses[0].city"


class TestValidate:
    def test_errors_are_collected(self, mapper: Mapper) -> None:
        """With `validate=True` every field error is collected into one `ValidationError`."""
        with pytest.raises(ValidationError) as info:
            mapper.map(dict[str, Any], PersonDC, {"age": "old"}, validate=True)

        assert len(info.value.errors) == 2
        assert {type(e) for e in info.value.errors} == {SourceNotFoundError, ConversionError}
        assert "2 mapping error(s)" in info.value.message

    def test_nested_errors_are_collected(self, mapper: Mapper) -> None:
        """Errors from nested objects are collected too."""
        with pytest.raises(ValidationError) as info:
            mapper.map(
                dict[str, Any],
                PersonWithAddressesDC,
                {"name": "Bob", "addresses": [{}, {}]},
                validate=True,
            )

        assert [str(e.dest) for e in info.value.errors] == [
            "PersonWithAddressesDC.addresses[0].city",
            "PersonWithAddressesDC.addresses[1].city",
        ]

    def test_valid_input_maps_normally(self, mapper: Mapper) -> None:
        """Validation mode does not change the result of a valid mapping."""
        result = mapper.map(dict[str, Any], PersonDC, {"name": "Bob", "age": 3}, validate=True)

        assert result == PersonDC("Bob", 3)


class TestMerge:
    def test_present_fields_are_overwritten(self, mapper: Mapper) -> None:
        """Merging assigns the present source fields on the existing destination."""
        dest = PersonDC("Bob", 3, tags=["a"])

        result = mapper.merge(dict[str, Any], {"age": 4}, dest)

        assert result is dest
        assert dest == PersonDC("Bob", 4, tags=["a"])

    def test_missing_fields_are_kept(self, mapper: Mapper) -> None:
        """A field absent from the source keeps its value, even without default."""
        dest = PersonDC("Bob", 3)

        mapper.merge(dict[str, Any], {}, dest)

        assert dest.name == "Bob"

    def test_nested_object_is_merged_in_place(self, mapper: Mapper) -> None:
        """An existing nested object is updated instead of being replaced."""
        address = AddressDC("Paris", "75000")
        dest = PersonDC("Bob", 3, address)

        mapper.merge(dict[str, Any], {"address": {"city": "Lyon"}}, dest)

        assert dest.address is address
        assert address == AddressDC("Lyon", "75000")

    def test_list_is_replaced_in_place(self, mapper: Mapper) -> None:
        """An existing list keeps its identity and receives the mapped items."""
        addresses = [AddressDC("Paris")]
        dest = PersonWithAddressesDC("Bob", addresses)

        mapper.merge(dict[str, Any], {"addresses": [{"city": "Lyon"}]}, dest)

        assert dest.addresses is addresses
        assert addresses == [AddressDC("Lyon")]

    def test_merge_into_typed_dict(self, mapper: Mapper) -> None:
        """Merging into a dictionary destination assigns keys."""
        dest: PersonDict = {"name": "Bob", "age": 3}

        mapper.map(dict[str, Any], PersonDict, {"nickname": "bobby"}, dest=dest)

        assert dest == {"name": "Bob", "age": 3, "nickname": "bobby"}


class TestProfiles:
    def test_map_from_renames_a_field(self, mapper: Mapper) -> None:
        """`map_from` reads the destination field from another source expression."""

        @dataclass
        class Src:
            full_name: str

        @dataclass
        class Dest:
            name: str

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(Src, Dest).for_attr(lambda d: d.name, lambda o: o.map_from(lambda s: s.full_name))

        mapper.load_profiles([MyProfile()])

        assert mapper.map(Src, Dest, Src("Bob")) == Dest("Bob")

    def test_map_from_nested_expression(self, mapper: Mapper) -> None:
        """`map_from` can walk attributes and items of the source."""

        @dataclass
        class Dest:
            city: str

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(
                    lambda d: d.city,
                    lambda o: o.map_from(lambda s: s.address.city),  # pyright: ignore[reportOptionalMemberAccess]
                )

        mapper.load_profiles([MyProfile()])

        assert mapper.map(PersonDC, Dest, PersonDC("Bob", 3, AddressDC("Paris"))) == Dest("Paris")

    def test_map_from_missing_path_is_absent(self, mapper: Mapper) -> None:
        """A source expression that hits `None` on the way yields an absent value."""

        @dataclass
        class Dest:
            city: str | None

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(
                    lambda d: d.city,
                    lambda o: o.map_from(lambda s: s.address.city),  # pyright: ignore[reportOptionalMemberAccess]
                )

        mapper.load_profiles([MyProfile()])

        assert mapper.map(PersonDC, Dest, PersonDC("Bob", 3)) == Dest(None)

    def test_ignore(self, mapper: Mapper) -> None:
        """An ignored field is never assigned, even when the source has it."""

        @dataclass
        class Dest:
            name: str
            age: int = 0

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(lambda d: d.age, lambda o: o.ignore())

        mapper.load_profiles([MyProfile()])

        assert mapper.map(PersonDC, Dest, PersonDC("Bob", 3)) == Dest("Bob", 0)

    def test_read_only(self, mapper: Mapper) -> None:
        """A read-only field is skipped."""

        @dataclass
        class Dest:
            name: str
            age: int = 0

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(lambda d: d.age, lambda o: o.read_only())

        mapper.load_profiles([MyProfile()])

        assert mapper.map(PersonDC, Dest, PersonDC("Bob", 3)) == Dest("Bob", 0)

    def test_default_factory(self, mapper: Mapper) -> None:
        """A default factory fills a field absent from the source."""

        @dataclass
        class Dest:
            name: str
            role: str

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(lambda d: d.role, lambda o: o.default(lambda: "guest"))

        mapper.load_profiles([MyProfile()])

        assert mapper.map(PersonDC, Dest, PersonDC("Bob", 3)) == Dest("Bob", "guest")

    def test_default_factory_is_not_used_when_present(self, mapper: Mapper) -> None:
        """A present source value wins over the default factory."""

        @dataclass
        class Dest:
            name: str

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(lambda d: d.name, lambda o: o.default(lambda: "guest"))

        mapper.load_profiles([MyProfile()])

        assert mapper.map(PersonDC, Dest, PersonDC("Bob", 3)) == Dest("Bob")

    def test_use_type_changes_conversion(self, mapper: Mapper) -> None:
        """`use_type` converts the value with another annotation than the declared one."""

        @dataclass
        class Dest:
            age: Any

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(dict[str, Any], Dest).for_attr(lambda d: d.age, lambda o: o.use_type(int))

        mapper.load_profiles([MyProfile()])

        assert mapper.map(dict[str, Any], Dest, {"age": "3"}) == Dest(3)

    def test_before_and_after_hooks_on_create(self, mapper: Mapper) -> None:
        """Both hooks run once the destination exists when creating."""
        calls: list[tuple[str, str]] = []

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, PersonDC).before_mapping(
                    lambda s, d: calls.append(("before", d.name))
                ).after_mapping(lambda s, d: calls.append(("after", d.name)))

        mapper.load_profiles([MyProfile()])
        mapper.map(PersonDC, PersonDC, PersonDC("Bob", 3))

        assert calls == [("before", "Bob"), ("after", "Bob")]

    def test_before_hook_runs_before_merge(self, mapper: Mapper) -> None:
        """When merging, the before hook sees the destination before assignment."""
        calls: list[tuple[str, str]] = []

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, PersonDC).before_mapping(
                    lambda s, d: calls.append(("before", d.name))
                ).after_mapping(lambda s, d: calls.append(("after", d.name)))

        mapper.load_profiles([MyProfile()])
        mapper.merge(PersonDC, PersonDC("Ann", 3), PersonDC("Bob", 3))

        assert calls == [("before", "Bob"), ("after", "Ann")]

    def test_include_inherits_overrides(self, mapper: Mapper) -> None:
        """`include` copies the overrides and hooks of a base mapping."""

        @dataclass
        class Src:
            full_name: str

        @dataclass
        class Base:
            name: str

        @dataclass
        class Child(Base):
            role: str = "user"

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(Src, Base).for_attr(lambda d: d.name, lambda o: o.map_from(lambda s: s.full_name))
                self.register(Src, Child).include(Src, Base)

        mapper.load_profiles([MyProfile()])

        assert mapper.map(Src, Child, Src("Bob")) == Child("Bob")

    def test_include_missing_base_raises(self, mapper: Mapper) -> None:
        """Including a mapping that was not registered is a configuration error."""

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, PersonDC).include(AddressDC, AddressDC)

        with pytest.raises(MappingConfigurationError, match="missing base mapping"):
            mapper.load_profiles([MyProfile()])

    def test_include_across_profiles(self, mapper: Mapper) -> None:
        """A base mapping loaded earlier can be included by a later profile."""

        @dataclass
        class Src:
            full_name: str

        @dataclass
        class Base:
            name: str

        @dataclass
        class Child(Base):
            pass

        class First(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(Src, Base).for_attr(lambda d: d.name, lambda o: o.map_from(lambda s: s.full_name))

        class Second(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(Src, Child).include(Src, Base)

        mapper.load_profiles([First()])
        mapper.load_profiles([Second()])

        assert mapper.map(Src, Child, Src("Bob")) == Child("Bob")

    def test_for_attr_requires_direct_attribute(self, mapper: Mapper) -> None:
        """Overrides only target direct attributes of the destination."""
        with pytest.raises(Exception, match="exceeds allowed depth"):
            Profile().register(PersonDC, PersonDC).for_attr(
                lambda d: d.address.city,  # pyright: ignore[reportOptionalMemberAccess]
                lambda o: o.ignore(),
            )


class TestConfigurationCheck:
    def test_valid_configuration_passes(self, mapper: Mapper) -> None:
        """A mapping whose required fields all have a source is valid."""

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, PersonModel)

        mapper.load_profiles([MyProfile()])

        mapper.assert_configuration_valid()

    def test_missing_required_field_is_reported(self, mapper: Mapper) -> None:
        """A required destination field the source cannot provide is reported with a hint."""

        @dataclass
        class Dest:
            name: str
            role: str

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest)

        mapper.load_profiles([MyProfile()])

        with pytest.raises(MappingConfigurationError, match=r"'role' is required.*for_attr\(lambda d: d\.role") as info:
            mapper.assert_configuration_valid()

        assert len(info.value.problems) == 1

    def test_override_satisfies_required_field(self, mapper: Mapper) -> None:
        """A default factory or source expression makes a required field valid."""

        @dataclass
        class Dest:
            name: str
            role: str

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(lambda d: d.role, lambda o: o.default(lambda: "x"))

        mapper.load_profiles([MyProfile()])

        mapper.assert_configuration_valid()

    def test_untyped_source_is_not_checked(self, mapper: Mapper) -> None:
        """A protocol that does not know its fields, like the `dict` one, disables the source check."""

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(dict[str, Any], PersonDC)

        mapper.load_profiles([MyProfile()])

        mapper.assert_configuration_valid()


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

    def test_mapping_decorator_forms(self, cache: Cache) -> None:
        """`mapping` and `mapping_protocol` accept both the bare and the parametrized forms."""

        @mapping
        class Bare(Profile):
            pass

        @mapping(cache=cache)
        class Parametrized(Profile):
            pass

        assert Bare.__name__ == "Bare"
        assert Parametrized.__name__ == "Parametrized"
        Cache.with_fallback(None).clear()

        with pytest.raises(TypeError):
            mapping(Bare, Parametrized)  # pyright: ignore[reportCallIssue]
        with pytest.raises(TypeError):
            mapping_protocol(1, 2)  # pyright: ignore[reportCallIssue]


@dataclass(frozen=True)
class Tag:
    name: str


@dataclass
class WithSetDC:
    tags: set[Tag] = field(default_factory=set[Tag])


@dataclass
class WithTupleDC:
    tags: tuple[Tag, ...] = ()


@dataclass
class WithInitFalseDC:
    a: int
    b: int = field(init=False, default=0)


class ReadOnlyProtocol(ObjectProtocol):
    """Wraps the dataclass protocol and marks the `age` field as not writable."""

    priority = 100

    def __init__(self) -> None:
        self._inner = DataclassProtocol()

    @override
    def matches(self, t: TWrap[Any]) -> bool:
        return self._inner.matches(t)

    @override
    def fields(self, t: TWrap[Any]) -> Mapping[str, FieldSpec]:
        specs = dict(self._inner.fields(t))
        if "age" in specs:
            spec = specs["age"]
            specs["age"] = FieldSpec(key=spec.key, type=spec.type, nullable=spec.nullable, writable=False)
        return specs

    @override
    def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
        return self._inner.read_field(obj, spec)

    @override
    def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
        return self._inner.construct(t, values)


class TestDecide:
    def _spec(self, **kwargs: Any) -> FieldSpec:
        return FieldSpec.from_type("x", int, **kwargs)

    def test_ignore_skips(self) -> None:
        """An ignored override skips the field whatever the source holds."""
        assert decide(1, self._spec(), MapMode.CREATE, FieldOverride(ignore=True)).action is Action.SKIP

    def test_not_writable_skips(self) -> None:
        """A non-writable field is skipped unless the override allows writing."""
        spec = self._spec(writable=False)

        assert decide(1, spec, MapMode.CREATE, NO_OVERRIDE).action is Action.SKIP
        assert decide(1, spec, MapMode.CREATE, FieldOverride(allow_write=True)).action is Action.ASSIGN

    def test_read_only_wins_over_allow_write(self) -> None:
        """`read_only` disables writing even when `allow_write` is set."""
        override = FieldOverride(read_only=True, allow_write=True)

        assert decide(1, self._spec(), MapMode.CREATE, override).action is Action.SKIP


class TestUtils:
    def test_is_value_type(self) -> None:
        """Scalars, dates, enums, unions and `None` are values; user classes are not."""
        assert is_value_type(wrap_type(int))
        assert is_value_type(wrap_type(datetime))
        assert is_value_type(wrap_type(int | str))
        assert is_value_type(wrap_type(None))
        assert not is_value_type(wrap_type(PersonDC))

    def test_dict_value_type(self) -> None:
        """`dict_value_type` returns the value wrap of a dict type, and `Any` for anything else."""
        assert dict_value_type(wrap_type(dict[str, int])).matches(int)
        assert dict_value_type(wrap_type(dict[Any, Any])).match(Any).is_exact
        assert dict_value_type(wrap_type(PersonDC)).match(Any).is_exact

    def test_element_type(self) -> None:
        """`element_type` returns the item wrap of a collection type, or `None`."""
        elem = element_type(wrap_type(list[AddressDC]))

        assert elem is not None
        assert elem.matches(AddressDC)
        bare = element_type(wrap_type(list[Any]))
        assert bare is not None
        assert bare.matches(Any)
        assert element_type(wrap_type(PersonDC)) is None
        assert element_type(wrap_type(int | str)) is None


class TestProtocolEdges:
    def test_fields_of_unsupported_types_are_empty(self) -> None:
        """Asking a protocol for the fields of a type it does not handle yields nothing."""
        for protocol in (DataclassProtocol(), PydanticProtocol(), TypedDictProtocol(), PlainObjectProtocol()):
            assert protocol.fields(wrap_type(int | str)) == {}

    def test_plain_fields_with_unresolved_forward_ref(self) -> None:
        """A plain class whose hints cannot be resolved has no fields."""

        class Broken:
            value: "Missing"  # noqa: F821  # pyright: ignore[reportUndefinedVariable]

        assert PlainObjectProtocol().fields(wrap_type(Broken)) == {}

    def test_read_field_on_wrong_object_kinds(self) -> None:
        """Reading a field from an object of the wrong kind yields `ABSENT`."""
        spec = FieldSpec.from_type("name", str)

        assert MappingProtocol().read_field(object(), spec) is ABSENT
        assert TypedDictProtocol().read_field(object(), spec) is ABSENT
        assert PydanticProtocol().read_field(object(), spec) is ABSENT
        assert PlainObjectProtocol().read_field(PlainPerson("x", 1), spec) == "x"
        assert PlainObjectProtocol().read_field(object(), spec) is ABSENT

    def test_construct_on_wrong_types_raises(self) -> None:
        """Constructing an unsupported type is a programming error."""
        with pytest.raises(TypeError):
            DataclassProtocol().construct(wrap_type(int), {})
        with pytest.raises(TypeError):
            PydanticProtocol().construct(wrap_type(int | str), {})
        with pytest.raises(InstantiationError):
            PlainObjectProtocol().construct(wrap_type(int | str), {})

    def test_mapping_protocol_dict_operations(self) -> None:
        """The `dict` protocol constructs and assigns plain dictionaries."""
        spec = FieldSpec.from_type("k", int)
        built = MappingProtocol().construct(wrap_type(dict[str, Any]), {"k": 1})
        MappingProtocol().assign(built, spec, 2)

        assert built == {"k": 2}

    def test_plain_construct_skips_variadic_parameters(self) -> None:
        """Variadic constructor parameters are ignored and remaining values are set as attributes."""

        class Flexible:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.args = args

        result: Any = PlainObjectProtocol().construct(wrap_type(Flexible), {"name": "x"})

        assert result.args == ()
        assert result.name == "x"

    def test_plain_construct_without_signature(self) -> None:
        """A class whose signature cannot be inspected is built without arguments."""
        result = PlainObjectProtocol().construct(wrap_type(dict[str, Any]), {})

        assert result == {}

    def test_plain_construct_failure(self, mapper: Mapper) -> None:
        """A constructor that raises is reported as an `InstantiationError`."""

        class Picky:
            name: str

            def __init__(self, name: str) -> None:
                raise ValueError(name)

        with pytest.raises(InstantiationError):
            mapper.map(dict[str, Any], Picky, {"name": "x"})

    def test_dataclass_init_false_field_is_assigned(self, mapper: Mapper) -> None:
        """A dataclass field excluded from the constructor is set after construction."""
        result = mapper.map(dict[str, Any], WithInitFalseDC, {"a": 1, "b": 2})

        assert (result.a, result.b) == (1, 2)

    def test_typed_dict_source(self, mapper: Mapper) -> None:
        """A `TypedDict` source reads its keys, missing optional keys are absent."""
        result = mapper.map(PersonDict, PersonDC, {"name": "Bob", "age": 3})

        assert result == PersonDC("Bob", 3)

    def test_untyped_source(self, mapper: Mapper) -> None:
        """A source declared as `Any` has no protocol and is read with `getattr`."""

        class Anything:
            def __init__(self) -> None:
                self.name = "Bob"
                self.age = 3

        result = mapper.map(cast(type[Any], Any), PersonDC, Anything())

        assert result == PersonDC("Bob", 3)


class TestMergeCollections:
    def test_set_is_replaced_in_place(self, mapper: Mapper) -> None:
        """An existing set keeps its identity and receives the mapped items."""
        tags: set[Tag] = {Tag("old")}
        dest = WithSetDC(tags)

        mapper.merge(dict[str, Any], {"tags": [{"name": "new"}]}, dest)

        assert dest.tags is tags
        assert tags == {Tag("new")}

    def test_other_collections_are_replaced(self, mapper: Mapper) -> None:
        """A collection that cannot be updated in place is replaced by the mapped list."""
        dest = WithTupleDC((Tag("old"),))

        mapper.merge(dict[str, Any], {"tags": [{"name": "new"}]}, dest)

        assert list(dest.tags) == [Tag("new")]


class TestValidateInstantiation:
    def test_instantiation_error_is_collected(self, mapper: Mapper) -> None:
        """In validation mode a failing constructor is collected instead of raised."""

        @dataclass
        class Picky:
            value: int

            def __post_init__(self) -> None:
                raise ValueError("nope")

        with pytest.raises(ValidationError) as info:
            mapper.map(dict[str, Any], Picky, {"value": 1}, validate=True)

        assert [type(e) for e in info.value.errors] == [InstantiationError]


class TestReadExpr:
    def test_item_access(self, mapper: Mapper) -> None:
        """`map_from` can index into dictionaries and lists of the source."""

        @dataclass
        class Src:
            extra: dict[str, Any]
            tags: list[str]

        @dataclass
        class Dest:
            first: str
            key: int

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(Src, Dest).for_attr(
                    lambda d: d.first, lambda o: o.map_from(lambda s: s.tags[0])
                ).for_attr(lambda d: d.key, lambda o: o.map_from(lambda s: s.extra["k"]))

        mapper.load_profiles([MyProfile()])

        assert mapper.map(Src, Dest, Src({"k": 1}, ["a"])) == Dest("a", 1)

    def test_missing_item_is_absent(self, mapper: Mapper) -> None:
        """A missing key or index yields an absent value."""

        @dataclass
        class Src:
            extra: dict[str, Any]

        @dataclass
        class Dest:
            key: int | None

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(Src, Dest).for_attr(lambda d: d.key, lambda o: o.map_from(lambda s: s.extra["k"]))

        mapper.load_profiles([MyProfile()])

        assert mapper.map(Src, Dest, Src({})) == Dest(None)

    def test_attribute_outside_protocol_fields(self, mapper: Mapper) -> None:
        """An attribute the protocol does not declare is read with `getattr`, absent when missing."""

        @dataclass
        class Dest:
            real: int
            missing: str | None

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, Dest).for_attr(
                    lambda d: d.real, lambda o: o.map_from(lambda s: s.age.real)
                ).for_attr(lambda d: d.missing, lambda o: o.map_from(lambda s: getattr(s, "nope")))  # noqa: B009

        mapper.load_profiles([MyProfile()])

        assert mapper.map(PersonDC, Dest, PersonDC("Bob", 3)) == Dest(3, None)

    def test_unsupported_node_raises(self, mapper: Mapper) -> None:
        """Only attribute and item access can be evaluated on a source."""

        class Call(ExpressionNode):
            @override
            def __expr_get_value__(self, obj: object) -> Any:
                return None

            @override
            def __expr_format__(self, depth: int | None) -> str:
                return "call()"

            @override
            def __expr_get_parents__(self) -> Iterable[ExpressionNode]:
                return []

        with pytest.raises(TypeError, match="only attribute and item access"):
            read_expr(Call(), object(), mapper.registry)


class TestAllowWrite:
    def test_allow_write_overrides_protocol(self, mapper: Mapper) -> None:
        """`allow_write` maps a field the protocol declares as not writable."""
        mapper.add_protocol(ReadOnlyProtocol())

        @dataclass
        class Dest:
            name: str
            age: int = 0

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(dict[str, Any], Dest).for_attr(lambda d: d.age, lambda o: o.allow_write())

        assert mapper.map(dict[str, Any], Dest, {"name": "Bob", "age": 3}).age == 0
        mapper.load_profiles([MyProfile()])
        assert mapper.map(dict[str, Any], Dest, {"name": "Bob", "age": 3}).age == 3


class TestConfigurationEdges:
    def test_destination_without_protocol_is_reported(self, mapper: Mapper) -> None:
        """A mapping to a type no protocol handles is an invalid configuration."""

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, int | str)  # pyright: ignore[reportArgumentType]

        mapper.load_profiles([MyProfile()])

        with pytest.raises(MappingConfigurationError, match="no protocol for destination"):
            mapper.assert_configuration_valid()

    def test_skipped_fields_are_not_required(self, mapper: Mapper) -> None:
        """Ignored and read-only fields need no source."""

        @dataclass
        class Dest:
            name: str
            role: str

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(AddressDC, Dest).for_attr(lambda d: d.name, lambda o: o.ignore()).for_attr(
                    lambda d: d.role, lambda o: o.read_only()
                )

        mapper.load_profiles([MyProfile()])

        mapper.assert_configuration_valid()

    def test_optional_fields_are_not_required(self, mapper: Mapper) -> None:
        """Nullable fields and fields with defaults need no source."""

        @dataclass
        class Dest:
            name: str
            role: str | None
            tags: list[str] = field(default_factory=list[str])

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(AddressDC, Dest).for_attr(lambda d: d.name, lambda o: o.map_from(lambda s: s.city))

        mapper.load_profiles([MyProfile()])

        mapper.assert_configuration_valid()


class TestDictDestination:
    def test_object_to_dict_copies_every_field(self, mapper: Mapper) -> None:
        """Mapping to a plain `dict` copies every readable source field under its key."""
        result = mapper.map(PersonDC, dict[str, Any], PersonDC("Bob", 3, tags=["a"]))

        assert result == {"name": "Bob", "age": 3, "address": None, "tags": ["a"]}

    def test_nested_objects_are_copied_as_is(self, mapper: Mapper) -> None:
        """With untyped values a nested object is placed in the dict without conversion."""
        address = AddressDC("Paris")

        result = mapper.map(PersonDC, dict[str, Any], PersonDC("Bob", 3, address))

        assert result["address"] is address

    def test_dict_to_dict(self, mapper: Mapper) -> None:
        """A dictionary source enumerates its own keys."""
        assert mapper.map(dict[str, Any], dict[str, Any], {"a": 1, "b": None}) == {"a": 1, "b": None}

    def test_typed_values_are_converted(self, mapper: Mapper) -> None:
        """The value type of the destination dict drives conversion."""
        assert mapper.map(dict[str, Any], dict[str, int], {"a": "1"}) == {"a": 1}

    def test_typed_values_reject_none_and_structures(self, mapper: Mapper) -> None:
        """A typed value dict refuses `None` and values that cannot be converted."""
        with pytest.raises(DestinationNotNullableError):
            mapper.map(dict[str, Any], dict[str, int], {"a": None})
        with pytest.raises(ConversionError):
            mapper.map(PersonDC, dict[str, int], PersonDC("Bob", 3, AddressDC("Paris")))

    def test_merge_into_dict_keeps_other_keys(self, mapper: Mapper) -> None:
        """Merging into an existing dict assigns the source keys and keeps the others."""
        dest: dict[str, Any] = {"kept": 1, "name": "Ann"}

        result = mapper.merge(PersonDC, PersonDC("Bob", 3), dest)

        assert result is dest
        assert dest == {"kept": 1, "name": "Bob", "age": 3, "address": None, "tags": []}

    def test_pydantic_unset_fields_are_not_copied(self, mapper: Mapper) -> None:
        """Fields not set on a pydantic source stay absent from the dict."""
        assert mapper.map(PersonModel, dict[str, Any], PersonModel(name="Bob", age=3)) == {"name": "Bob", "age": 3}

    def test_overrides_apply_to_dict_destinations(self, mapper: Mapper) -> None:
        """Profile overrides on source keys work when the destination is a dict."""

        class MyProfile(Profile):
            def __init__(self) -> None:
                super().__init__()
                self.register(PersonDC, dict[str, Any]).for_attr(lambda d: d["age"], lambda o: o.ignore())

        mapper.load_profiles([MyProfile()])

        assert "age" not in mapper.map(PersonDC, dict[str, Any], PersonDC("Bob", 3))

    def test_instance_fields_on_non_dict(self) -> None:
        """The dict protocol has no instance fields for anything but a dictionary."""
        assert MappingProtocol().instance_fields(object(), wrap_type(dict[str, Any])) == {}
        assert DataclassProtocol().instance_fields(PersonDC("Bob", 3), wrap_type(PersonDC)).keys() == {
            "name",
            "age",
            "address",
            "tags",
        }


class TestSequenceDestination:
    def test_list_of_dicts_to_list_of_dataclasses(self, mapper: Mapper) -> None:
        result = mapper.map(
            list[dict[str, Any]], list[PersonDC], [{"name": "Bob", "age": 3}, {"name": "Ann", "age": 4}]
        )

        assert result == [PersonDC("Bob", 3), PersonDC("Ann", 4)]

    def test_tuple_and_set_destinations(self, mapper: Mapper) -> None:
        assert mapper.map(list[Any], tuple[int, ...], ["1", "2"]) == (1, 2)
        assert mapper.map(list[Any], set[int], ["1", "1", "2"]) == {1, 2}
        assert mapper.map(list[Any], frozenset[str], ["a", "a", "b"]) == frozenset({"a", "b"})

    def test_set_source_is_enumerated(self, mapper: Mapper) -> None:
        assert sorted(mapper.map(set[str], list[int], {"1", "2"})) == [1, 2]

    def test_untyped_elements_pass_through(self, mapper: Mapper) -> None:
        person = PersonDC("Bob", 3)

        assert mapper.map(list[Any], [person, 1])[0] is person

    def test_nested_sequences(self, mapper: Mapper) -> None:
        result = mapper.map(list[Any], list[list[PersonDC]], [[{"name": "Bob", "age": 3}]])

        assert result == [[PersonDC("Bob", 3)]]

    def test_errors_carry_the_index_path(self, mapper: Mapper) -> None:
        with pytest.raises(ValidationError) as info:
            mapper.map(list[Any], list[PersonDC], [{"name": "Bob", "age": 3}, {"name": "Ann"}], validate=True)

        assert len(info.value.errors) == 1
        assert isinstance(info.value.errors[0], SourceNotFoundError)
        assert str(info.value.errors[0].dest).endswith("[1].age")

    def test_non_iterable_source_has_no_fields(self, mapper: Mapper) -> None:
        assert mapper.map(int, list[int], 1) == []
        assert SequenceProtocol().instance_fields("abc", wrap_type(list[str])) == {}
        assert SequenceProtocol().read_field(object(), FieldSpec.from_type("0", int)) is ABSENT

    def test_merge_into_a_list_assigns_by_index_and_appends(self, mapper: Mapper) -> None:
        dest: list[int] = [9, 9]

        result = mapper.merge(list[Any], [1, 2, 3], dest)

        assert result is dest
        assert dest == [1, 2, 3]

    def test_merge_into_a_set_adds(self, mapper: Mapper) -> None:
        dest: set[int] = {9}

        mapper.merge(list[Any], [1], dest)

        assert dest == {9, 1}

    def test_merge_into_immutable_collections_fails(self, mapper: Mapper) -> None:
        with pytest.raises(TypeError):
            mapper.merge(list[Any], [1], (9,))
        with pytest.raises(TypeError):
            mapper.merge(list[Any], [1], frozenset({9}))

    def test_protocol_shape(self) -> None:
        assert SequenceProtocol().fields(wrap_type(list[int])) == {}
        assert not SequenceProtocol().knows_fields
        assert str(SequenceProtocol().value_type(wrap_type(list[int]))) == "int"
        assert str(SequenceProtocol().value_type(wrap_type(cast(Any, list)))) == "Any"
        assert str(dict_value_type(wrap_type(cast(Any, dict)))) == "Any"
        assert str(ObjectProtocol.value_type(PlainObjectProtocol(), wrap_type(PersonDC))) == "Any"
        assert SequenceProtocol().construct(wrap_type(cast(Any, list[int] | tuple[int, ...])), {"1": 2, "0": 1}) == [
            1,
            2,
        ]
