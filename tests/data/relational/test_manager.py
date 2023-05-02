import pytest
from sqlalchemy import ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from bolinette import Cache, meta
from bolinette.ext.data import DatabaseManager
from bolinette.ext.data.databases import _DatabaseConnection
from bolinette.ext.data.exceptions import DataError, EntityError
from bolinette.ext.data.relational import (
    DeclarativeMeta,
    EntityManager,
    EntityMeta,
    RelationalDatabase,
    Repository,
    SessionManager,
    entity,
    get_base,
    repository,
)
from bolinette.testing import Mock
from bolinette.utils import StringUtils


class _MockedRelationalDatabase(RelationalDatabase):
    def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
        pass


def create_entity_base(cache: Cache, name: str = "TestDatabase") -> type[DeclarativeBase]:
    base = type(name, (DeclarativeBase,), {})
    meta.set(base, DeclarativeMeta("test"))
    cache.add(DeclarativeMeta, base)
    return base


def mock_db_manager(mock: Mock, engine_type: type[RelationalDatabase] | None = None) -> None:
    def _get_connection(name: str) -> _DatabaseConnection:
        return _DatabaseConnection(name, "protocol://", False, engine_type or _MockedRelationalDatabase)

    mock.mock(DatabaseManager).setup("has_connection", lambda _: True).setup("get_connection", _get_connection)


def mock_entities(cache: Cache, name: str, base: type[DeclarativeBase]) -> type[DeclarativeBase]:
    entity_type = type(
        StringUtils.capitalize(name),
        (base,),
        {"__tablename__": name, "id": mapped_column(Integer, primary_key=True)},
    )
    meta.set(entity_type, EntityMeta(name, entity_key=[getattr(entity_type, "id")]))
    cache.add(EntityMeta, entity_type)
    return entity_type


def test_init_engines() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache)
    mock_db_manager(mock)

    manager = mock.injection.require(EntityManager)

    assert len(manager._engines) == 1
    assert base in manager._engines


def test_fail_init_engines_unknown_connection() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    create_entity_base(cache)

    mock.mock(DatabaseManager).setup("has_connection", lambda _: False)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert "No 'test' database connection defined in environment" == info.value.message


def test_fail_init_engines_non_relational_system() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    create_entity_base(cache)

    def _get_connection(name: str) -> _DatabaseConnection:
        return _DatabaseConnection(name, "sqlite+aiosqlite://", False, object)

    mock.mock(DatabaseManager).setup("has_connection", lambda _: True).setup("get_connection", _get_connection)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert "Database connection 'test' is not a relational system" == info.value.message


async def test_create_all() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    visited = []

    class _MockedRelationalDatabase(RelationalDatabase):
        def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
            self._name = name

        async def create_all(self) -> None:
            visited.append(self._name)

    create_entity_base(cache)
    mock_db_manager(mock, _MockedRelationalDatabase)

    manager = mock.injection.require(EntityManager)

    await manager.create_all()

    assert visited == ["test"]


def test_open_sessions() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    visited = []

    class _MockedRelationalDatabase(RelationalDatabase):
        def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
            self._name = name

        def open_session(self, sessions: SessionManager) -> None:
            visited.append(self._name)

    create_entity_base(cache)
    mock_db_manager(mock, _MockedRelationalDatabase)

    manager = mock.injection.require(EntityManager)

    manager.open_sessions(SessionManager())

    assert visited == ["test"]


def test_init_entities() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache)
    mock_db_manager(mock)
    entity_type = mock_entities(cache, "entity", base)

    manager = mock.injection.require(EntityManager)

    assert len(manager._entities) == 1
    assert entity_type in manager._entities
    assert meta.has(entity_type, RelationalDatabase)
    assert manager.is_entity_type(entity_type)
    assert not manager.is_entity_type(object)


def test_fail_init_entities_multiple_bases() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base1 = create_entity_base(cache, "TestDatabase1")
    base2 = create_entity_base(cache, "TestDatabase2")
    mock_db_manager(mock)

    entity_type = type(
        "Entity", (base1, base2), {"__tablename__": "entity", "id": mapped_column(Integer, primary_key=True)}
    )
    meta.set(entity_type, EntityMeta("entity", entity_key=[getattr(entity_type, "id")]))
    cache.add(EntityMeta, entity_type)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert f"Entity {entity_type} cannot inherit from multiple declarative bases" == info.value.message


def test_fail_init_entities_unknown_base() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = type("TestDatabase", (DeclarativeBase,), {})
    mock_db_manager(mock)
    entity_type = mock_entities(cache, "entity", base)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert f"Entity {entity_type} has no known bases as its parents" == info.value.message


def test_init_entity_composite_entity_key() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache, "TestDatabase")
    mock_db_manager(mock)

    entity_type = type(
        "Entity",
        (base,),
        {
            "__tablename__": "entity",
            "id": mapped_column(Integer, primary_key=True),
            "firstname": mapped_column(String),
            "lastname": mapped_column(String),
            "__table_args__": (UniqueConstraint("firstname", "lastname"),),
        },
    )
    meta.set(
        entity_type,
        EntityMeta("entity", entity_key=[getattr(entity_type, "firstname"), getattr(entity_type, "lastname")]),
    )
    cache.add(EntityMeta, entity_type)

    assert isinstance(entity_type.__table__, Table)

    mock.injection.require(EntityManager)


def test_fail_init_entity_key_not_unique() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache, "TestDatabase")
    mock_db_manager(mock)

    entity_type = type(
        "Entity",
        (base,),
        {"__tablename__": "entity", "id": mapped_column(Integer, primary_key=True), "name": mapped_column(String)},
    )
    meta.set(entity_type, EntityMeta("entity", entity_key=[getattr(entity_type, "name")]))
    cache.add(EntityMeta, entity_type)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert f"Entity {entity_type}, Entity key does not match with any unique constraint" == info.value.message


def test_fail_init_entity_wrong_table_object() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache, "TestDatabase")
    mock_db_manager(mock)

    entity_type = type("Entity", (base,), {"__tablename__": "entity", "id": mapped_column(Integer, primary_key=True)})
    meta.set(entity_type, EntityMeta("entity", entity_key=[getattr(entity_type, "id")]))
    cache.add(EntityMeta, entity_type)

    entity_type.__table__ = object()  # type: ignore

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert f"Entity {entity_type}, Could not determine entity key" == info.value.message


def test_fail_init_entity_wrong_constraint_type() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache, "TestDatabase")
    mock_db_manager(mock)

    entity_type = type(
        "Entity",
        (base,),
        {"__tablename__": "entity", "id": mapped_column(Integer, primary_key=True), "name": mapped_column(String)},
    )
    meta.set(entity_type, EntityMeta("entity", entity_key=[getattr(entity_type, "name")]))
    cache.add(EntityMeta, entity_type)

    assert isinstance(entity_type.__table__, Table)
    entity_type.__table__.constraints = [object()]  # type: ignore

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert f"Entity {entity_type}, Entity key does not match with any unique constraint" == info.value.message


def test_init_repositories() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache)
    mock_db_manager(mock)
    entity_type1 = mock_entities(cache, "entity1", base)
    entity_type2 = mock_entities(cache, "entity2", base)

    @repository(entity_type2, cache=cache)
    class _Entity2Repository(Repository[entity_type2]):
        pass

    mock.injection.require(EntityManager)

    assert mock.injection.is_registered(Repository[entity_type1])
    assert mock.injection.is_registered(Repository[entity_type2])
    assert mock.injection.is_registered(_Entity2Repository)


def test_fail_init_repositories_unused_repository() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache)
    mock_db_manager(mock)
    entity_type = type("Entity", (base,), {"__tablename__": "entity", "id": mapped_column(Integer, primary_key=True)})
    meta.set(entity_type, EntityMeta("entity", entity_key=[getattr(entity_type, "id")]))

    @repository(entity_type, cache=cache)
    class _EntityRepository(Repository[entity_type]):
        pass

    with pytest.raises(DataError) as info:
        mock.injection.require(EntityManager)

    assert f"Repository {_EntityRepository} was not used with any registered entity" == info.value.message


def test_fail_declare_entity_attribute_not_found() -> None:
    cache = Cache()

    class _Entity(get_base("test", cache=cache)):
        __tablename__ = "entity"
        id: Mapped[int] = mapped_column(primary_key=True)

    with pytest.raises(EntityError) as info:
        entity(entity_key=["none"])(_Entity)

    assert f"Entity {_Entity}, Attribute 'none' not found" == info.value.message


def test_fail_declare_entity_attribute_not_column() -> None:
    cache = Cache()

    class _Parent(get_base("test", cache=cache)):
        __tablename__ = "parent"
        id: Mapped[int] = mapped_column(primary_key=True)

    class _Child(get_base("test", cache=cache)):
        __tablename__ = "child"
        id: Mapped[int] = mapped_column(primary_key=True)
        parent_id: Mapped[int] = mapped_column(ForeignKey("parent.id"))
        parent: Mapped[_Parent] = relationship()

    with pytest.raises(EntityError) as info:
        entity(entity_key=["parent"])(_Child)

    assert f"Entity {_Child}, Attribute 'parent' is not an SQLAlchemy mapped column" == info.value.message
