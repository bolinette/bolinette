import pytest

from bolinette.core import Cache, Logger
from bolinette.core.testing import Mock
from bolinette.core.utils import AttributeUtils
from bolinette.data import EntityManager, entity
from bolinette.data.exceptions import EntityError


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

    assert Test in manager._entities
    assert manager._entities[Test].name == "test"
    assert len(manager._entities[Test].attributes) == 3
    assert "id" in manager._entities[Test].attributes
    assert "name" in manager._entities[Test].attributes
    assert "price" in manager._entities[Test].attributes


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

    assert Test in manager._entities
    assert "id" in manager._entities[Test].attributes
    assert not manager._entities[Test].attributes["id"].nullable
    assert manager._entities[Test].attributes["id"].py_type is int
    assert "name" in manager._entities[Test].attributes
    assert manager._entities[Test].attributes["name"].nullable
    assert manager._entities[Test].attributes["name"].py_type is str


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

    assert "test_name_u" in manager._entities[Test].constraints
    assert len(manager._entities[Test].constraints["test_name_u"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._entities[Test].constraints["test_name_u"].columns)) == ["name"]  # type: ignore


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

    assert "custom_name" in manager._entities[Test].constraints
    assert "test_name_u" not in manager._entities[Test].constraints
    assert len(manager._entities[Test].constraints["custom_name"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._entities[Test].constraints["custom_name"].columns)) == ["name"]  # type: ignore


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

    assert "test_firstname_lastname_u" in manager._entities[Test].constraints
    assert len(manager._entities[Test].constraints["test_firstname_lastname_u"].columns) == 2  # type: ignore
    assert list(map(lambda c: c.name, manager._entities[Test].constraints["test_firstname_lastname_u"].columns)) == ["firstname", "lastname"]  # type: ignore


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

    assert "test_name_u" in manager._entities[Test].constraints
    assert len(manager._entities[Test].constraints["test_name_u"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._entities[Test].constraints["test_name_u"].columns)) == ["name"]  # type: ignore


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

    assert "unique_column" in manager._entities[Test].constraints
    assert "test_name_u" not in manager._entities[Test].constraints
    assert len(manager._entities[Test].constraints["unique_column"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._entities[Test].constraints["unique_column"].columns)) == ["name"]  # type: ignore


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

    assert "test_pk" in manager._entities[Test].constraints
    assert len(manager._entities[Test].constraints["test_pk"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._entities[Test].constraints["test_pk"].columns)) == ["id"]  # type: ignore


def test_entity_primary_key_column_decorator():
    cache = Cache()

    @entity(cache=cache)
    @entity.column("id").primary_key()
    class Test:
        id: int

    mock = _setup_mock(cache)
    manager = mock.injection.require(EntityManager)

    assert "test_pk" in manager._entities[Test].constraints
    assert len(manager._entities[Test].constraints["test_pk"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._entities[Test].constraints["test_pk"].columns)) == ["id"]  # type: ignore


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

    assert "custom_name" in manager._entities[Test].constraints
    assert "test_pk" not in manager._entities[Test].constraints
    assert len(manager._entities[Test].constraints["custom_name"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._entities[Test].constraints["custom_name"].columns)) == ["id"]  # type: ignore


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


def test_entity_foreign_key() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.foreign_key("parent_id", target=Parent)
    class Child:
        id: int
        parent_id: int

    mock = _setup_mock(cache)
    mock.injection.require(EntityManager)


def test_entity_foreign_key_with_reference() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.foreign_key("parent_id", reference="parent")
    class Child:
        id: int
        parent_id: int
        parent: Parent


def test_entity_foreign_key_column_decorator() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_id").foreign_key(target=Parent)
    class Child:
        id: int
        parent_id: int


def test_entity_foreign_key_column_decorator_reference() -> None:
    cache = Cache()

    @entity(cache=cache)
    @entity.primary_key("id")
    class Parent:
        id: int

    @entity(cache=cache)
    @entity.primary_key("id")
    @entity.column("parent_id").foreign_key(reference="parent")
    class Child:
        id: int
        parent_id: int
        parent: Parent
