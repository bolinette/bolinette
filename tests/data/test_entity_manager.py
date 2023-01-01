from typing import Annotated

import pytest

from bolinette import Cache, Logger
from bolinette.ext.data import (
    EntityManager,
    ForeignKey,
    Format,
    ManyToOne,
    OneToMany,
    PrimaryKey,
    Unique,
    entity,
)
from bolinette.ext.data.exceptions import EntityError
from bolinette.ext.data.manager import (
    CollectionReference,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    TableReference,
    UniqueConstraint,
)
from bolinette.testing import Mock
from bolinette.utils import AttributeUtils


def _setup_mock(cache: Cache) -> Mock:
    mock = Mock(cache=cache)
    mock.injection.add(AttributeUtils, "singleton")
    mock.injection.add(EntityManager, "singleton")
    mock.mock(Logger[EntityManager]).dummy()
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

    assert Test in manager.definitions
    assert manager.definitions[Test].name == "test"
    assert len(manager.definitions[Test].columns) == 3

    assert "id" in manager.definitions[Test].columns
    assert "name" in manager.definitions[Test].columns
    assert "price" in manager.definitions[Test].columns


def test_entity_nullable_attribute():
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: str | None

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert Test in manager.definitions

    assert "id" in manager.definitions[Test].columns
    assert not manager.definitions[Test].columns["id"].nullable
    assert manager.definitions[Test].columns["id"].py_type is int

    assert "name" in manager.definitions[Test].columns
    assert manager.definitions[Test].columns["name"].nullable
    assert manager.definitions[Test].columns["name"].py_type is str


def test_define_entity_column_format():
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        email: Annotated[str, Format("email")]
        password: Annotated[str, Format("password")]

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert manager.definitions[Test].columns["email"].format == "email"
    assert manager.definitions[Test].columns["password"].format == "password"


def test_entity_unique_constraint() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: Annotated[int, PrimaryKey()]
        name: Annotated[str, Unique()]

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "test_name_u" in manager.definitions[Test].constraints
    constraint = manager.definitions[Test].constraints["test_name_u"]
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

    assert "custom_name" in manager.definitions[Test].constraints
    assert "test_name_u" not in manager.definitions[Test].constraints
    constraint = manager.definitions[Test].constraints["custom_name"]
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

    assert "test_fullname_u" in manager.definitions[Test].constraints
    constraint = manager.definitions[Test].constraints["test_fullname_u"]
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

    assert "test_id_pk" in manager.definitions[Test].constraints
    constraint = manager.definitions[Test].constraints["test_id_pk"]
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

    assert "custom_name" in manager.definitions[Test].constraints
    assert "test_id_pk" not in manager.definitions[Test].constraints
    constraint = manager.definitions[Test].constraints["custom_name"]
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

    assert "parent" not in manager.definitions[Child].references
    assert "child_parent_fk" in manager.definitions[Child].constraints
    fk = manager.definitions[Child].constraints["child_parent_fk"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.columns)) == ["parent_id"]
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

    assert "parent" not in manager.definitions[Child].references
    assert "custom_name" in manager.definitions[Child].constraints
    fk = manager.definitions[Child].constraints["custom_name"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.columns)) == [
        "parent_id1",
        "parent_id2",
    ]
    assert list(map(lambda c: c.name, fk.target_columns)) == ["id1", "id2"]


def test_fail_entity_foreign_key_length_mismatch() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id1: int
        parent_id2: int

        custom_name = ForeignKey(Parent, ["parent_id1", "parent_id2"])

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'custom_name', Source columns in foreign key do not match with target columns"
        == info.value.message
    )


def test_fail_entity_foreign_key_type_mismatch() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: Annotated[str, ForeignKey(Parent)]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent_id', Source columns in foreign key do not match with target columns"
        == info.value.message
    )


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


def test_entity_many_to_one() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: Annotated[int, ForeignKey(Parent)]
        parent: Annotated[Parent, ManyToOne(["parent_id"], lazy=False)]

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" in manager.definitions[Child].references
    ref = manager.definitions[Child].references["parent"]
    assert isinstance(ref, TableReference)
    assert ref.table.entity is Child
    assert ref.target.entity is Parent
    assert ref.lazy is False


def test_fail_entity_many_to_one_unknown_column() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent: Annotated[Parent, ManyToOne(["parent_id"])]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Column 'parent_id' does not exist in entity"
        == info.value.message
    )


def test_fail_entity_many_to_one_not_a_foreign_key() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: int
        parent: Annotated[Parent, ManyToOne(["parent_id"])]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Columns defined in reference do not match with any foreign key"
        == info.value.message
    )


def test_fail_entity_many_to_one_wrong_type() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent1:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Parent2:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: Annotated[int, ForeignKey(Parent1)]
        parent: Annotated[Parent2, ManyToOne(["parent_id"])]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Reference type is not the same as foreign key target entity"
        == info.value.message
    )


def test_fail_entity_unused_reference() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent: Parent

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Reference to {Parent} does not define any relationship"
        == info.value.message
    )


def test_fail_entity_many_to_one_on_collection_reference() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: Annotated[int, ForeignKey(Parent)]
        parent: Annotated[list[Parent], ManyToOne(["parent_id"])]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Many-to-one relationship must be a single reference"
        == info.value.message
    )


def test_fail_entity_many_to_one_unknown_backref() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parent_id: Annotated[int, ForeignKey(Parent)]
        parent: Annotated[Parent, ManyToOne(["parent_id"], other_side="children")]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Relationship 'children' does not exist on type {Parent}"
        == info.value.message
    )


class ParentA:
    id: Annotated[int, PrimaryKey()]
    child_id: "Annotated[int, ForeignKey(ChildA)]"  # type: ignore
    child: "Annotated[ChildA, ManyToOne(['child_id'], other_side='parent')]"


class ChildA:
    id: Annotated[int, PrimaryKey()]
    parent_id: Annotated[int, ForeignKey(ParentA)]
    parent: Annotated[ParentA, ManyToOne(["parent_id"], other_side="child")]


def test_fail_entity_many_to_one_collection_backref() -> None:
    cache = Cache()

    entity(cache=cache)(ParentA)
    entity(cache=cache)(ChildA)

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {ParentA}, Attribute 'child', Relationship 'parent' must be a collection reference"
        == info.value.message
    )


class ParentB:
    id: Annotated[int, PrimaryKey()]
    children: "Annotated[list[ChildB], OneToMany(['parent_id'], lazy=False)]"


class ChildB:
    id: Annotated[int, PrimaryKey()]
    parent_id: Annotated[int, ForeignKey(ParentB)]


def test_entity_one_to_many() -> None:
    cache = Cache()

    entity(cache=cache)(ParentB)
    entity(cache=cache)(ChildB)

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "children" in manager.definitions[ParentB].references
    ref = manager.definitions[ParentB].references["children"]
    assert isinstance(ref, CollectionReference)
    assert ref.table.entity is ParentB
    assert ref.target.entity is ChildB
    assert ref.lazy is False
    assert ref.other_side is None


def test_fail_entity_one_to_many_on_single_reference() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Parent:
        id: Annotated[int, PrimaryKey()]

    @entity(cache=cache)
    class Child:
        id: Annotated[int, PrimaryKey()]
        parents: Annotated[Parent, OneToMany([], other_side="children")]

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parents', One-to-many relationship must be a collection reference"
        == info.value.message
    )


class ParentC:
    id: Annotated[int, PrimaryKey()]
    child_id: "Annotated[int, ForeignKey(ChildC)]"  # type: ignore
    children: "Annotated[list[ChildC], OneToMany(['parent_id'], other_side='parents')]"


class ChildC:
    id: Annotated[int, PrimaryKey()]
    parent_id: Annotated[int, ForeignKey(ParentC)]
    parents: Annotated[list[ParentC], OneToMany(["child_id"], other_side="children")]


def test_fail_entity_one_to_many_collection_backref() -> None:
    cache = Cache()

    entity(cache=cache)(ParentC)
    entity(cache=cache)(ChildC)

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {ParentC}, Attribute 'children', Relationship 'parents' must be a single reference"
        == info.value.message
    )


class ChildD:
    id: Annotated[int, PrimaryKey()]
    parent_id: "Annotated[int, ForeignKey(ParentD)]"  # type: ignore


class ParentD:
    id: Annotated[int, PrimaryKey()]
    children: Annotated[list[ChildD], OneToMany(["parent_id"], other_side="parent")]


def test_fail_entity_one_to_many_unknown_backref() -> None:
    cache = Cache()

    entity(cache=cache)(ParentD)
    entity(cache=cache)(ChildD)

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {ParentD}, Attribute 'children', Relationship 'parent' does not exist on type {ChildD}"
        == info.value.message
    )


class ParentE:
    id: Annotated[int, PrimaryKey()]
    children: "Annotated[list[ChildE], OneToMany(['parent_id'], other_side='parent', lazy=False)]"


class ChildE:
    id: Annotated[int, PrimaryKey()]
    parent_id: Annotated[int, ForeignKey(ParentE)]
    parent: Annotated[
        ParentE, ManyToOne(["parent_id"], other_side="children", lazy=True)
    ]


def test_entity_one_to_many_and_many_to_one() -> None:
    cache = Cache()

    entity(cache=cache)(ParentE)
    entity(cache=cache)(ChildE)

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" in manager.definitions[ChildE].references
    ref_c = manager.definitions[ChildE].references["parent"]
    assert isinstance(ref_c, TableReference)
    assert ref_c.table.entity is ChildE
    assert ref_c.target.entity is ParentE
    assert ref_c.lazy is True

    assert "children" in manager.definitions[ParentE].references
    ref_p = manager.definitions[ParentE].references["children"]
    assert isinstance(ref_p, CollectionReference)
    assert ref_p.table.entity is ParentE
    assert ref_p.target.entity is ChildE
    assert ref_p.lazy is False

    assert ref_p.other_side is ref_c
    assert ref_c.other_side is ref_p
