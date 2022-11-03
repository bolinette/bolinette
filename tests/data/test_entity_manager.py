from typing import Annotated

import pytest

from bolinette.core import Cache, Logger
from bolinette.core.testing import Mock
from bolinette.core.utils import AttributeUtils
from bolinette.data import EntityManager, ForeignKey, Format, PrimaryKey, Unique, entity
from bolinette.data.exceptions import EntityError
from bolinette.data.manager import (
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
)


def _setup_mock(cache: Cache) -> Mock:
    mock = Mock(cache=cache)
    mock.injection.add(AttributeUtils, "singleton")
    mock.injection.add(EntityManager, "singleton")
    mock.mock(Logger).dummy()
    return mock


def test_define_entity():
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: str
        price: float

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert Test in manager._table_defs
    assert manager._table_defs[Test].name == "test"
    assert len(manager._table_defs[Test].columns) == 3

    assert "id" in manager._table_defs[Test].columns
    assert "name" in manager._table_defs[Test].columns
    assert "price" in manager._table_defs[Test].columns


def test_entity_nullable_attribute():
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: str | None

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert Test in manager._table_defs

    assert "id" in manager._table_defs[Test].columns
    assert not manager._table_defs[Test].columns["id"].nullable
    assert manager._table_defs[Test].columns["id"].py_type is int

    assert "name" in manager._table_defs[Test].columns
    assert manager._table_defs[Test].columns["name"].nullable
    assert manager._table_defs[Test].columns["name"].py_type is str


def test_define_entity_column_format():
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        email: Annotated[str, Format("email")]
        password: Annotated[str, Format("password")]

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert manager._table_defs[Test].columns["email"].format == "email"
    assert manager._table_defs[Test].columns["password"].format == "password"


def test_entity_unique_constraint() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: Annotated[str, Unique()]

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "test_name_u" in manager._table_defs[Test].constraints
    constraint = manager._table_defs[Test].constraints["test_name_u"]
    assert isinstance(constraint, UniqueConstraint)
    assert list(map(lambda c: c.name, constraint.columns)) == ["name"]


def test_entity_unique_constraint_custom_name() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: Annotated[str, Unique(name="custom_name")]

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "custom_name" in manager._table_defs[Test].constraints
    assert "test_name_u" not in manager._table_defs[Test].constraints
    constraint = manager._table_defs[Test].constraints["custom_name"]
    assert isinstance(constraint, UniqueConstraint)
    assert list(map(lambda c: c.name, constraint.columns)) == ["name"]


def test_fail_entity_unique_constraint_custom_columns() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: Annotated[str, Unique(["name"])]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'name', Annotated unique constraint must not provide columns"
        == info.value.message
    )


def test_fail_entity_unique_constraint_no_custom_name() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: str

        u = Unique(name="u")

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'u', Class level unique constraint must not define a custom name"
        == info.value.message
    )


def test_fail_entity_unique_constraint_no_custom_columns() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: str

        u = Unique()

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'u', Class level unique constraint must provide columns"
        == info.value.message
    )


def test_fail_entity_column_union_type() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: str | bool

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'name', Union types are not allowed"
        == info.value.message
    )


def test_entity_unique_constraint_class_level() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        firstname: str
        lastname: str

        test_fullname_u = Unique(["firstname", "lastname"])

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "test_fullname_u" in manager._table_defs[Test].constraints
    constraint = manager._table_defs[Test].constraints["test_fullname_u"]
    assert isinstance(constraint, UniqueConstraint)
    assert list(map(lambda c: c.name, constraint.columns)) == ["firstname", "lastname"]


def test_fail_entity_unique_constraint_invalid_column() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: str

        test_name_u = Unique(["firstname"])

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'test_name_u', Unique constraint does not reference a valid column 'firstname'"
        == info.value.message
    )


def test_fail_entity_unique_constraint_duplicated() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: Annotated[int, Unique()]

        test_custom_u = Unique(["name"])

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'test_custom_u', A similar unique constraint has already been defined by 'test_name_u'"
        == info.value.message
    )


def test_entity_primary_key():
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "test_id_pk" in manager._table_defs[Test].constraints
    constraint = manager._table_defs[Test].constraints["test_id_pk"]
    assert isinstance(constraint, PrimaryKeyConstraint)
    assert list(map(lambda c: c.name, constraint.columns)) == ["id"]


def test_fail_entity_two_primary_keys():
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id1: Annotated[int, PrimaryKey()]
        id2: Annotated[int, PrimaryKey()]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Several primary keys have been defined" == info.value.message
    )


def test_entity_primary_key_custom_name():
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey(name="custom_name")]

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "custom_name" in manager._table_defs[Test].constraints
    assert "test_id_pk" not in manager._table_defs[Test].constraints
    constraint = manager._table_defs[Test].constraints["custom_name"]
    assert isinstance(constraint, PrimaryKeyConstraint)
    assert list(map(lambda c: c.name, constraint.columns)) == ["id"]


def test_fail_entity_no_primary_key() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert f"Entity {Test}, No primary keys have been defined" == info.value.message


def test_fail_entity_primary_key_custom_columns() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey(["id"])]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'id', Annotated primary key must not provide columns"
        == info.value.message
    )


def test_fail_entity_primary_key_no_custom_name() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: int

        pk = PrimaryKey(name="pk")

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'pk', Class level primary key must not define a custom name"
        == info.value.message
    )


def test_fail_entity_primary_key_no_custom_columns() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: int

        pk = PrimaryKey()

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'pk', Class level primary key must provide columns"
        == info.value.message
    )


def test_fail_entity_primary_key_invalid_column() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: int

        test_pk = PrimaryKey(["none"])

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'test_pk', Primary key does not reference a valid column 'none'"
        == info.value.message
    )


def test_fail_entity_primary_key_duplicated_unique() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id1: int
        id2: int

        test_pk = PrimaryKey(["id1", "id2"])
        test_u = Unique(["id1", "id2"])

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'test_pk', A unique constraint has already been defined by 'test_u'"
        == info.value.message
    )


def test_fail_entity_reference_not_registered() -> None:
    cache = Cache()

    class Parent:
        id: int

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent: Parent

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Type {Parent} is not supported"
        == info.value.message
    )


def test_entity_foreign_key() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: Annotated[int, ForeignKey(Parent)]

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" not in manager._table_defs[Child].references
    assert "child_parent_fk" in manager._table_defs[Child].constraints
    fk = manager._table_defs[Child].constraints["child_parent_fk"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.target_columns)) == ["id"]


def test_entity_foreign_key_to_composite() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id1: int
        id2: int

        parent_pk = PrimaryKey(["id1", "id2"])

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id1: int
        parent_id2: int

        custom_name = ForeignKey(Parent, ["parent_id1", "parent_id2"])

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" not in manager._table_defs[Child].references
    assert "custom_name" in manager._table_defs[Child].constraints
    fk = manager._table_defs[Child].constraints["custom_name"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.target_columns)) == ["id1", "id2"]


def test_fail_entity_foreign_key_custom_columns() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: Annotated[int, ForeignKey(Parent, ["parent_id"])]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent_id', Annotated foreign key must not provide columns"
        == info.value.message
    )


def test_fail_entity_foreign_key_no_custom_name() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: int

        fk = ForeignKey(Parent, name="fk")

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'fk', Class level foreign key must not define a custom name"
        == info.value.message
    )


def test_fail_entity_foreign_key_no_custom_columns() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: int

        fk = ForeignKey(Parent)

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'fk', Class level foreign key must provide columns"
        == info.value.message
    )


def test_fail_entity_foreign_key_not_an_entity() -> None:
    cache = Cache()

    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: Annotated[int, ForeignKey(Parent)]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent_id', Type {Parent} is not a registered entity"
        == info.value.message
    )


# def test_entity_many_to_one_with_reference() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id1", "id2")
#     class Parent:
#         id1: int
#         id2: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_one("parent_id1", "parent_id2", reference="parent")
#     class Child:
#         id: int
#         parent_id1: int
#         parent_id2: int
#         parent: Parent

#     mock = _setup_mock(cache)
#     manager = mock.injection.require(EntityManager)

#     assert "parent" in manager._table_defs[Child].references
#     ref = manager._table_defs[Child].references["parent"]
#     assert isinstance(ref, TableReference)
#     assert ref.target.entity is Parent
#     assert "child_parent_fk" in manager._table_defs[Child].constraints
#     fk = manager._table_defs[Child].constraints["child_parent_fk"]
#     assert isinstance(fk, ManyToOneConstraint)
#     assert fk.target.entity is Parent
#     assert list(map(lambda c: c.name, fk.target_columns)) == ["id1", "id2"]


# def test_entity_many_to_one_column_decorator() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.column("parent_id").many_to_one(target=Parent)
#     class Child:
#         id: int
#         parent_id: int

#     mock = _setup_mock(cache)
#     manager = mock.injection.require(EntityManager)

#     assert "parent" not in manager._table_defs[Child].references
#     assert "child_parent_fk" in manager._table_defs[Child].constraints
#     fk = manager._table_defs[Child].constraints["child_parent_fk"]
#     assert isinstance(fk, ManyToOneConstraint)
#     assert fk.target.entity is Parent
#     assert list(map(lambda c: c.name, fk.target_columns)) == ["id"]


# def test_entity_many_to_one_column_decorator_reference() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.column("parent_id").many_to_one(reference="parent")
#     class Child:
#         id: int
#         parent_id: int
#         parent: Parent

#     mock = _setup_mock(cache)
#     manager = mock.injection.require(EntityManager)

#     assert "parent" in manager._table_defs[Child].references
#     ref = manager._table_defs[Child].references["parent"]
#     assert isinstance(ref, TableReference)
#     assert ref.target.entity is Parent
#     assert "child_parent_fk" in manager._table_defs[Child].constraints
#     fk = manager._table_defs[Child].constraints["child_parent_fk"]
#     assert isinstance(fk, ManyToOneConstraint)
#     assert fk.target.entity is Parent
#     assert list(map(lambda c: c.name, fk.target_columns)) == ["id"]


# def test_fail_entity_many_to_one_unknown_column() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_one("parent_id", reference="parent")
#     class Test:
#         id: int

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Test}, 'parent_id' in foreign key does not match with an entity column"
#         == info.value.message
#     )


# def test_fail_entity_many_to_one_unknown_reference() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_one("parent_id", reference="parent")
#     class Test:
#         id: int
#         parent_id: int

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Test}, 'parent' in foreign key does not match with any reference in the entity"
#         == info.value.message
#     )


# def test_fail_entity_many_to_one_unknown_foreign_target() -> None:
#     cache = Cache()

#     class Parent:
#         pass

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_one("parent_id", target=Parent)
#     class Child:
#         id: int
#         parent_id: int

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, Type {Parent} provided in foreign key is not a registered entity"
#         == info.value.message
#     )


# def test_fail_entity_many_to_one_reference_used_twice() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_one("parent_id1", reference="parent")
#     @entity.many_to_one("parent_id2", reference="parent")
#     class Child:
#         id: int
#         parent: Parent
#         parent_id1: int
#         parent_id2: int

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, Reference 'parent' is already used by another relationship"
#         == info.value.message
#     )


# def test_entity_many_to_one_custom_key() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.column("name").unique()
#     class Parent:
#         id: int
#         name: str

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.column("parent_name").many_to_one(reference="parent", target_columns="name")
#     class Child:
#         id: int
#         parent_name: str
#         parent: Parent

#     mock = _setup_mock(cache)
#     manager = mock.injection.require(EntityManager)

#     assert "parent" in manager._table_defs[Child].references
#     ref = manager._table_defs[Child].references["parent"]
#     assert isinstance(ref, TableReference)
#     assert ref.target.entity is Parent
#     assert "child_parent_fk" in manager._table_defs[Child].constraints
#     fk = manager._table_defs[Child].constraints["child_parent_fk"]
#     assert isinstance(fk, ManyToOneConstraint)
#     assert fk.target.entity is Parent
#     assert list(map(lambda c: c.name, fk.target_columns)) == ["name"]


# def test_fail_entity_many_to_one_target_column_unknown() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.column("parent_name").many_to_one(reference="parent", target_columns="name")
#     class Child:
#         id: int
#         parent_name: str
#         parent: Parent

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, 'name' is not a column in entity {Parent}"
#         == info.value.message
#     )


# def test_fail_entity_many_to_one_target_column_not_unique() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int
#         name: str

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.column("parent_name").many_to_one(reference="parent", target_columns="name")
#     class Child:
#         id: int
#         parent_name: str
#         parent: Parent

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, (name) target in foreign key is not a unique constraint on entity {Parent}"
#         == info.value.message
#     )


# def test_fail_entity_many_to_one_target_column_not_unique_bis() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int
#         name: str

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_one("parent_name", reference="parent", target_columns="name")
#     class Child:
#         id: int
#         parent_name: str
#         parent: Parent

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, (name) target in foreign key is not a unique constraint on entity {Parent}"
#         == info.value.message
#     )


# def test_fail_entity_many_to_one_type_mismatch() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.column("parent_id").many_to_one(reference="parent")
#     class Child:
#         id: int
#         parent_id: str
#         parent: Parent

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, Foreign key to target {Parent} does not have the same column types on both sides"
#         == info.value.message
#     )


# def test_fail_entity_many_to_one_length() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id1", "id2")
#     class Parent:
#         id1: int
#         id2: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.column("parent_id").many_to_one(reference="parent")
#     class Child:
#         id: int
#         parent_id: int
#         parent: Parent

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, Foreign key to target {Parent} does not have the same column count on both sides"
#         == info.value.message
#     )


# def test_entity_many_to_many() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Entity1:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_many("entities")
#     class Entity2:
#         id: int
#         entities: list[Entity1]

#     mock = _setup_mock(cache)

#     manager = mock.injection.require(EntityManager)

#     assert "entities" in manager._table_defs[Entity2].references
#     ref = manager._table_defs[Entity2].references["entities"]
#     assert isinstance(ref, CollectionReference)
#     assert ref.element.entity is Entity1
#     assert "entity2_entity1_fk" in manager._table_defs[Entity2].constraints
#     const = manager._table_defs[Entity2].constraints["entity2_entity1_fk"]
#     assert isinstance(const, ManyToManyConstraint)
#     assert const.join_table == "entity2_entity1"
#     assert const.target.entity is Entity1
#     assert list(map(lambda c: c.name, const.source_columns)) == ["id"]
#     assert list(map(lambda c: c.name, const.target_columns)) == ["id"]


# def test_fail_entity_many_to_many_unknown_reference() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_many("entities")
#     class Entity:
#         id: int

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Entity}, 'entities' in foreign key does not match with any reference in the entity"
#         == info.value.message
#     )


# def test_fail_entity_many_to_many_wrong_reference_type() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Entity1:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_many("entities")
#     class Entity2:
#         id: int
#         entities: Entity1

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Entity2}, Many-to-many reference 'entities' must be a list of entities"
#         == info.value.message
#     )


# def test_entity_many_to_many_manual_columns() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.unique("name")
#     class Entity1:
#         id: int
#         name: str

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.unique("name")
#     @entity.many_to_many("entities", source_columns="name", target_columns="name")
#     class Entity2:
#         id: int
#         name: str
#         entities: list[Entity1]

#     mock = _setup_mock(cache)

#     manager = mock.injection.require(EntityManager)

#     assert "entities" in manager._table_defs[Entity2].references
#     ref = manager._table_defs[Entity2].references["entities"]
#     assert isinstance(ref, CollectionReference)
#     assert ref.element.entity is Entity1
#     assert "entity2_entity1_fk" in manager._table_defs[Entity2].constraints
#     const = manager._table_defs[Entity2].constraints["entity2_entity1_fk"]
#     assert isinstance(const, ManyToManyConstraint)
#     assert const.join_table == "entity2_entity1"
#     assert const.target.entity is Entity1
#     assert list(map(lambda c: c.name, const.source_columns)) == ["name"]
#     assert list(map(lambda c: c.name, const.target_columns)) == ["name"]


# def test_entity_many_to_many_composite_manual_columns() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.unique("index", "name")
#     class Entity1:
#         id: int
#         index: int
#         name: str

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.unique("index", "name")
#     @entity.many_to_many(
#         "entities", source_columns=["index", "name"], target_columns=["index", "name"]
#     )
#     class Entity2:
#         id: int
#         index: int
#         name: str
#         entities: list[Entity1]

#     mock = _setup_mock(cache)
#     manager = mock.injection.require(EntityManager)

#     assert "entities" in manager._table_defs[Entity2].references
#     ref = manager._table_defs[Entity2].references["entities"]
#     assert isinstance(ref, CollectionReference)
#     assert ref.element.entity is Entity1
#     assert "entity2_entity1_fk" in manager._table_defs[Entity2].constraints
#     const = manager._table_defs[Entity2].constraints["entity2_entity1_fk"]
#     assert isinstance(const, ManyToManyConstraint)
#     assert const.join_table == "entity2_entity1"
#     assert const.target.entity is Entity1
#     assert list(map(lambda c: c.name, const.source_columns)) == ["index", "name"]
#     assert list(map(lambda c: c.name, const.target_columns)) == ["index", "name"]


# def test_fail_entity_many_to_many_unknown_source_column() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Entity1:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_many("entities", source_columns="name")
#     class Entity2:
#         id: int
#         entities: list[Entity1]

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Entity2}, 'name' in foreign key does not match with an entity column"
#         == info.value.message
#     )


# def test_fail_entity_many_to_many_unknown_target_column() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Entity1:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_many("entities", target_columns="name")
#     class Entity2:
#         id: int
#         entities: list[Entity1]

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Entity2}, 'name' in foreign key does not match with an column in target entity {Entity1}"
#         == info.value.message
#     )


# def test_fail_entity_reference_too_few_list_args() -> None:
#     cache = Cache()

#     class Entity1:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Entity2:
#         id: int
#         entities: list[Entity1]

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Entity2}, Attribute 'entities', Type {Entity1} is not a registered entity"
#         == info.value.message
#     )


# @entity.primary_key("id")
# class ParentA:
#     id: int
#     children: "list[ChildA]"


# @entity.primary_key("id")
# @entity.many_to_one(
#     "parent_id", reference="parent", lazy=False, backref=("children", "subquery")
# )
# class ChildA:
#     id: int
#     parent_id: int
#     parent: ParentA


# def test_entity_many_to_one_backref() -> None:
#     cache = Cache()

#     entity(cache=cache)(ParentA)
#     entity(cache=cache)(ChildA)

#     mock = _setup_mock(cache)
#     manager = mock.injection.require(EntityManager)

#     assert "children" in manager._table_defs[ParentA].references
#     ref = manager._table_defs[ParentA].references["children"]
#     assert isinstance(ref, CollectionReference)
#     assert ref.element.entity is ChildA
#     assert ref.other_side is not None
#     assert ref.lazy == "subquery"
#     assert isinstance(ref.other_side, TableReference)
#     assert ref.other_side.table.entity is ChildA

#     assert "parent" in manager._table_defs[ChildA].references
#     ref = manager._table_defs[ChildA].references["parent"]
#     assert isinstance(ref, TableReference)
#     assert ref.target.entity is ParentA
#     assert ref.other_side is not None
#     assert ref.lazy is False
#     assert isinstance(ref.other_side, CollectionReference)
#     assert ref.other_side.table.entity is ParentA


# def test_fail_entity_many_to_one_backref_no_target_ref() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_one("parent_id", reference="parent", backref="children")
#     class Child:
#         id: int
#         parent_id: int
#         parent: Parent

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, 'children' in backref does not match with any reference in the target entity {Parent}"
#         == info.value.message
#     )


# @entity.primary_key("id")
# class ParentB:
#     id: int
#     children: "ChildB"


# @entity.primary_key("id")
# @entity.many_to_one("parent_id", reference="parent", backref="children")
# class ChildB:
#     id: int
#     parent_id: int
#     parent: ParentB


# def test_fail_entity_many_to_one_backref_not_a_list() -> None:
#     cache = Cache()

#     entity(cache=cache)(ParentB)
#     entity(cache=cache)(ChildB)

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {ChildB}, Many-to-one backref 'children' in {ParentB} must be a list"
#         == info.value.message
#     )


# @entity.primary_key("id")
# class ParentC:
#     id: int
#     children: "list[ChildC]"


# @entity.primary_key("id")
# @entity.many_to_one("parent_id1", reference="parent1", backref="children")
# @entity.many_to_one("parent_id2", reference="parent2", backref="children")
# class ChildC:
#     id: int
#     parent_id1: int
#     parent1: ParentC
#     parent_id2: int
#     parent2: ParentC


# def test_fail_entity_many_to_one_backref_already_in_use() -> None:
#     cache = Cache()

#     entity(cache=cache)(ParentC)
#     entity(cache=cache)(ChildC)

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {ChildC}, Backref 'children' in {ParentC} is already used by another relationship"
#         == info.value.message
#     )


# @entity.primary_key("id")
# class ParentD:
#     id: int
#     children: "list[ChildD]"


# @entity.primary_key("id")
# @entity.many_to_many("parents", lazy=False, backref=("children", "subquery"))
# class ChildD:
#     id: int
#     parents: list[ParentD]


# def test_entity_many_to_many_backref() -> None:
#     cache = Cache()

#     entity(cache=cache)(ParentD)
#     entity(cache=cache)(ChildD)

#     mock = _setup_mock(cache)
#     manager = mock.injection.require(EntityManager)

#     assert "children" in manager._table_defs[ParentD].references
#     ref = manager._table_defs[ParentD].references["children"]
#     assert isinstance(ref, CollectionReference)
#     assert ref.element.entity is ChildD
#     assert ref.other_side is not None
#     assert ref.lazy == "subquery"
#     assert isinstance(ref.other_side, CollectionReference)
#     assert ref.other_side.table.entity is ChildD

#     assert "parents" in manager._table_defs[ChildD].references
#     ref = manager._table_defs[ChildD].references["parents"]
#     assert isinstance(ref, CollectionReference)
#     assert ref.element.entity is ParentD
#     assert ref.other_side is not None
#     assert ref.lazy is False
#     assert isinstance(ref.other_side, CollectionReference)
#     assert ref.other_side.table.entity is ParentD


# def test_fail_entity_many_to_many_backref_no_target_ref() -> None:
#     cache = Cache()

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     class Parent:
#         id: int

#     @entity(cache=cache)
#     @entity.primary_key("id")
#     @entity.many_to_many("parents", backref="children")
#     class Child:
#         id: int
#         parents: list[Parent]

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {Child}, 'children' in backref does not match with any reference in the target entity {Parent}"
#         == info.value.message
#     )


# @entity.primary_key("id")
# class ParentE:
#     id: int
#     children: "ChildE"


# @entity.primary_key("id")
# @entity.many_to_many("parents", backref="children")
# class ChildE:
#     id: int
#     parents: list[ParentE]


# def test_fail_entity_many_to_many_backref_not_a_list() -> None:
#     cache = Cache()

#     entity(cache=cache)(ParentE)
#     entity(cache=cache)(ChildE)

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {ChildE}, Many-to-many backref 'children' in {ParentE} must be a list"
#         == info.value.message
#     )


# @entity.primary_key("id")
# class ParentF:
#     id: int
#     children: "list[ChildF]"


# @entity.primary_key("id")
# @entity.many_to_many("parents1", backref="children")
# @entity.many_to_many("parents2", backref="children")
# class ChildF:
#     id: int
#     parents1: list[ParentF]
#     parents2: list[ParentF]


# def test_fail_entity_many_to_many_backref_already_in_use() -> None:
#     cache = Cache()

#     entity(cache=cache)(ParentF)
#     entity(cache=cache)(ChildF)

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {ChildF}, Backref 'children' in {ParentF} is already used by another relationship"
#         == info.value.message
#     )


# @entity.primary_key("id")
# class ParentG:
#     id: int


# @entity.primary_key("id")
# @entity.many_to_many("parents")
# @entity.many_to_many("parents")
# class ChildG:
#     id: int
#     parents: list[ParentG]


# def test_fail_entity_many_to_many_reference_used_twice() -> None:
#     cache = Cache()

#     entity(cache=cache)(ParentG)
#     entity(cache=cache)(ChildG)

#     mock = _setup_mock(cache)

#     with pytest.raises(EntityError) as info:
#         mock.injection.require(EntityManager)

#     assert (
#         f"Entity {ChildG}, Reference 'parents' is already used by another relationship"
#         == info.value.message
#     )
