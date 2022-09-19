import pytest

from bolinette.core import Cache, Logger
from bolinette.core.testing import Mock
from bolinette.core.utils import AttributeUtils
from bolinette.data import EntityManager, entity
from bolinette.data.exceptions import EntityError
from bolinette.data.manager import ForeignKeyConstraint


def _setup_mock(cache: Cache) -> Mock:
    mock = Mock(cache=cache)
    mock.injection.add(AttributeUtils, "singleton")
    mock.injection.add(EntityManager, "singleton")
    mock.mock(Logger).dummy()
    return mock


def test_define_entity():
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Test:
        id: int
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


def test_fail_entity_unkown_column_decorator():
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("name").unique()
    class Test:
        id: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, 'name' in entity decorator does not match with any column"
        in info.value.message
    )


def test_entity_nullable_attribute():
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Test:
        id: int
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


def test_entity_unique_constraint() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.unique("name")
    class Test:
        id: int
        name: str

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "test_name_u" in manager._table_defs[Test].constraints
    assert len(manager._table_defs[Test].constraints["test_name_u"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._table_defs[Test].constraints["test_name_u"].columns)) == ["name"]  # type: ignore


def test_entity_unique_constraint_custom_name() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.unique("name", name="custom_name")
    class Test:
        id: int
        name: str

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "custom_name" in manager._table_defs[Test].constraints
    assert "test_name_u" not in manager._table_defs[Test].constraints
    assert len(manager._table_defs[Test].constraints["custom_name"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._table_defs[Test].constraints["custom_name"].columns)) == ["name"]  # type: ignore


def test_fail_entity_column_union_type() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Test:
        id: int | None
        name: str | bool

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Attribute 'name', Union types are not allowed"
        in info.value.message
    )


def test_entity_unique_constraint_multi_columns() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.unique("firstname", "lastname")
    class Test:
        id: int
        firstname: str
        lastname: str

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "test_firstname_lastname_u" in manager._table_defs[Test].constraints
    assert len(manager._table_defs[Test].constraints["test_firstname_lastname_u"].columns) == 2  # type: ignore
    assert list(map(lambda c: c.name, manager._table_defs[Test].constraints["test_firstname_lastname_u"].columns)) == ["firstname", "lastname"]  # type: ignore


def test_entity_unique_constraint_single_column() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("name").unique()
    class Test:
        id: int
        name: str

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "test_name_u" in manager._table_defs[Test].constraints
    assert len(manager._table_defs[Test].constraints["test_name_u"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._table_defs[Test].constraints["test_name_u"].columns)) == ["name"]  # type: ignore


def test_entity_unique_constraint_single_column_custom_name() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("name").unique(name="unique_column")
    class Test:
        id: int
        name: str

    mock = _setup_mock(cache)

    manager = mock.injection.require(EntityManager)

    assert "unique_column" in manager._table_defs[Test].constraints
    assert "test_name_u" not in manager._table_defs[Test].constraints
    assert len(manager._table_defs[Test].constraints["unique_column"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._table_defs[Test].constraints["unique_column"].columns)) == ["name"]  # type: ignore


def test_fail_entity_unique_constraint_invalid_column() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.unique("_name")
    class Test:
        id: int
        name: str

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, '_name' in unique constraint does not refer to an entity column"
        in info.value.message
    )


def test_fail_entity_unique_constraint_duplicated() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.unique("firstname", "lastname")
    @entity.unique("lastname", "firstname")
    class Test:
        id: int
        firstname: str
        lastname: str

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Several unique constraints are defined on the same columns"
        in info.value.message
    )


def test_entity_primary_key():
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Test:
        id: int

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "test_pk" in manager._table_defs[Test].constraints
    assert len(manager._table_defs[Test].constraints["test_pk"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._table_defs[Test].constraints["test_pk"].columns)) == ["id"]  # type: ignore


def test_entity_primary_key_column_decorator():
    cache = Cache()

    @entity(cache=cache)
    @entity.column("id").primary_key()
    class Test:
        id: int

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "test_pk" in manager._table_defs[Test].constraints
    assert len(manager._table_defs[Test].constraints["test_pk"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._table_defs[Test].constraints["test_pk"].columns)) == ["id"]  # type: ignore


def test_fail_entity_two_primary_keys():
    cache = Cache()

    @entity(cache=cache)
    @entity.column("id1").primary_key()
    @entity.column("id2").primary_key()
    class Test:
        id1: int
        id2: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Several columns have been marked as primary"
        in info.value.message
    )


def test_fail_entity_two_primary_keys_bis():
    cache = Cache()

    @entity(cache=cache)
    @entity.column("id1").primary_key()
    @entity.primary_key("id2")
    class Test:
        id1: int
        id2: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Several columns have been marked as primary"
        in info.value.message
    )


def test_entity_primary_key_custom_name():
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id", name="custom_name")
    class Test:
        id: int

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "custom_name" in manager._table_defs[Test].constraints
    assert "test_pk" not in manager._table_defs[Test].constraints
    assert len(manager._table_defs[Test].constraints["custom_name"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._table_defs[Test].constraints["custom_name"].columns)) == ["id"]  # type: ignore


def test_fail_entity_no_primary_key() -> None:
    cache = Cache()

    @entity(cache=cache)
    class Test:
        id: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert f"Entity {Test}, No primary key defined" in info.value.message


def test_fail_entity_primary_key_invalid_column() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("none")
    class Test:
        id: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, 'none' in primary key does not refer to an entity column"
        in info.value.message
    )


def test_fail_entity_primary_key_duplicated_unique() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id1", "id2")
    @entity.unique("id2", "id1")
    class Test:
        id1: int
        id2: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, Primary key is defined on the same columns as a unique constraint"
        in info.value.message
    )


def test_fail_entity_reference_not_registered() -> None:
    cache = Cache()

    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    class Child:
        id: int
        parent: Parent

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Type {Parent} is not supported"
        in info.value.message
    )


def test_entity_many_to_one() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.many_to_one("parent_id", target=Parent)
    class Child:
        id: int
        parent_id: int

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" not in manager._table_defs[Child].references
    assert "child_parent_fk" in manager._table_defs[Child].constraints
    fk = manager._table_defs[Child].constraints["child_parent_fk"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.target_columns)) == ["id"]


def test_entity_many_to_one_with_reference() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id1", "id2")
    class Parent:
        id1: int
        id2: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.many_to_one("parent_id1", "parent_id2", reference="parent")
    class Child:
        id: int
        parent_id1: int
        parent_id2: int
        parent: Parent

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" in manager._table_defs[Child].references
    assert manager._table_defs[Child].references["parent"].target.entity is Parent
    assert "child_parent_fk" in manager._table_defs[Child].constraints
    fk = manager._table_defs[Child].constraints["child_parent_fk"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.target_columns)) == ["id1", "id2"]


def test_entity_many_to_one_column_decorator() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_id").many_to_one(target=Parent)
    class Child:
        id: int
        parent_id: int

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" not in manager._table_defs[Child].references
    assert "child_parent_fk" in manager._table_defs[Child].constraints
    fk = manager._table_defs[Child].constraints["child_parent_fk"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.target_columns)) == ["id"]


def test_entity_many_to_one_column_decorator_reference() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_id").many_to_one(reference="parent")
    class Child:
        id: int
        parent_id: int
        parent: Parent

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" in manager._table_defs[Child].references
    assert manager._table_defs[Child].references["parent"].target.entity is Parent
    assert "child_parent_fk" in manager._table_defs[Child].constraints
    fk = manager._table_defs[Child].constraints["child_parent_fk"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.target_columns)) == ["id"]


def test_fail_entity_many_to_one_unknown_column() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.many_to_one("parent_id", reference="parent")
    class Test:
        id: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, 'parent_id' in foreign key does not match with an entity column"
        in info.value.message
    )


def test_fail_entity_many_to_one_unknown_reference() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.many_to_one("parent_id", reference="parent")
    class Test:
        id: int
        parent_id: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Test}, 'parent' in foreign_key does not match with any reference in the entity"
        in info.value.message
    )


def test_fail_entity_many_to_one_unknown_foreign_target() -> None:
    cache = Cache()

    class Parent:
        pass

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.many_to_one("parent_id", target=Parent)
    class Child:
        id: int
        parent_id: int

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, Type {Parent} provided in foreign key is not a registered entity"
        in info.value.message
    )


def test_entity_many_to_one_custom_key() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("name").unique()
    class Parent:
        id: int
        name: str

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_name").many_to_one(reference="parent", target_columns="name")
    class Child:
        id: int
        parent_name: str
        parent: Parent

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "parent" in manager._table_defs[Child].references
    assert manager._table_defs[Child].references["parent"].target.entity is Parent
    assert "child_parent_fk" in manager._table_defs[Child].constraints
    fk = manager._table_defs[Child].constraints["child_parent_fk"]
    assert isinstance(fk, ForeignKeyConstraint)
    assert fk.target.entity is Parent
    assert list(map(lambda c: c.name, fk.target_columns)) == ["name"]


def test_fail_entity_many_to_one_target_column_unknown() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_name").many_to_one(reference="parent", target_columns="name")
    class Child:
        id: int
        parent_name: str
        parent: Parent

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, 'name' is not a column in entity {Parent}"
        in info.value.message
    )


def test_fail_entity_many_to_one_target_column_not_unique() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int
        name: str

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_name").many_to_one(reference="parent", target_columns="name")
    class Child:
        id: int
        parent_name: str
        parent: Parent

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, (name) target in foreign key is not a unique constraint on entity {Parent}"
        in info.value.message
    )


def test_fail_entity_many_to_one_type_mismatch() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_id").many_to_one(reference="parent")
    class Child:
        id: int
        parent_id: str
        parent: Parent

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, (parent_id) foreign key and {Parent}(id) do not match"
        in info.value.message
    )


def test_fail_entity_many_to_one_length() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id1", "id2")
    class Parent:
        id1: int
        id2: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_id").many_to_one(reference="parent")
    class Child:
        id: int
        parent_id: int
        parent: Parent

    mock = _setup_mock(cache)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert (
        f"Entity {Child}, (parent_id) foreign key and {Parent}(id1,id2) do not match"
        in info.value.message
    )
