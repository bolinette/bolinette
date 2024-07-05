from typing import override

import pytest
from sqlalchemy import Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, mapped_column

from bolinette.core import Cache, meta
from bolinette.core.exceptions import InitError
from bolinette.core.logging import Logger
from bolinette.core.testing import Mock
from bolinette.core.utils import StringUtils
from bolinette.data import DatabaseManager
from bolinette.data.databases import DatabaseConnection
from bolinette.data.exceptions import EntityError
from bolinette.data.relational import (
    AbstractDatabase,
    AsyncRelationalDatabase,
    AsyncTransaction,
    DeclarativeMeta,
    EntityManager,
    EntityMeta,
    Repository,
    repository,
)


class _MockedRelationalDatabase(AsyncRelationalDatabase):
    def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
        pass


def create_entity_base(cache: Cache, name: str = "TestDatabase") -> type[DeclarativeBase]:
    base = type(name, (DeclarativeBase,), {})
    meta.set(base, DeclarativeMeta("test"))
    cache.add(DeclarativeMeta, base)
    return base


def mock_db_manager(mock: Mock, engine_type: type[AsyncRelationalDatabase] | None = None) -> None:
    def _get_connection(name: str) -> DatabaseConnection:
        return DatabaseConnection(name, "protocol://", False, engine_type or _MockedRelationalDatabase)

    (
        mock.mock(DatabaseManager)
        .setup_callable(lambda m: m.has_connection, lambda name: True)
        .setup_callable(lambda m: m.get_connection, _get_connection)
    )


def mock_entities(cache: Cache, name: str, base: type[DeclarativeBase]) -> type[DeclarativeBase]:
    entity_type = type(
        StringUtils.capitalize(name),
        (base,),
        {"__tablename__": name, "id": mapped_column(Integer, primary_key=True)},
    )
    meta.set(entity_type, EntityMeta(name))
    cache.add(EntityMeta, entity_type)
    return entity_type


def test_init_engines() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache)
    mock_db_manager(mock)

    manager = mock.injection.require(EntityManager)

    assert len(manager.engines) == 1
    assert base in manager.engines


def test_fail_init_engines_unknown_connection() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    create_entity_base(cache)

    mock.mock(DatabaseManager).setup_callable(lambda m: m.has_connection, lambda name: False)

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert "No 'test' database connection defined in environment" == info.value.message


def test_fail_init_engines_non_relational_system() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    create_entity_base(cache)

    def _get_connection(name: str) -> DatabaseConnection:
        return DatabaseConnection(name, "sqlite+aiosqlite://", False, object)

    (
        mock.mock(DatabaseManager)
        .setup_callable(lambda m: m.has_connection, lambda name: True)
        .setup_callable(lambda m: m.get_connection, _get_connection)
    )

    with pytest.raises(EntityError) as info:
        mock.injection.require(EntityManager)

    assert "Database connection 'test' is not a relational system" == info.value.message


async def test_create_all() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    visited: list[str] = []

    class _MockedRelationalDatabase(AsyncRelationalDatabase):
        def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
            self._name = name

        @override
        async def create_all(self) -> None:
            visited.append(self._name)

    create_entity_base(cache)
    mock_db_manager(mock, _MockedRelationalDatabase)

    manager = mock.injection.require(EntityManager)

    await manager.create_all()

    assert visited == ["test"]


async def test_open_sessions() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")
    mock.injection.add(AsyncTransaction, "scoped")
    mock.mock(Logger[AsyncTransaction]).dummy()

    visited: list[str] = []

    class _MockedRelationalDatabase(AsyncRelationalDatabase):
        def __init__(self, base: type[DeclarativeBase], name: str, uri: str, echo: bool):
            self._name = name

        @override
        def open_session(self, sessions: AsyncTransaction, /) -> None:
            visited.append(self._name)

    create_entity_base(cache)
    mock_db_manager(mock, _MockedRelationalDatabase)

    async with mock.injection.get_async_scoped_session() as scoped_inject:
        scoped_inject.require(AsyncTransaction)

    assert visited == ["test"]


def test_init_entities() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache)
    mock_db_manager(mock)
    entity_type = mock_entities(cache, "entity", base)

    manager = mock.injection.require(EntityManager)

    assert len(manager.entities) == 1
    assert entity_type in manager.entities
    assert meta.has(entity_type, AbstractDatabase)
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
    meta.set(entity_type, EntityMeta("entity"))
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
        EntityMeta("entity"),
    )
    cache.add(EntityMeta, entity_type)

    assert isinstance(entity_type.__table__, Table)

    mock.injection.require(EntityManager)


def test_init_repositories() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add(EntityManager, "singleton")

    base = create_entity_base(cache)
    mock_db_manager(mock)
    entity_type1 = mock_entities(cache, "entity1", base)
    entity_type2 = mock_entities(cache, "entity2", base)

    @repository(cache=cache)
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
    meta.set(entity_type, EntityMeta("entity"))

    @repository(cache=cache)
    class _EntityRepository(Repository[entity_type]):
        pass

    with pytest.raises(InitError) as info:
        mock.injection.require(EntityManager)

    assert f"Repository {_EntityRepository}, entity {entity_type} is not a registered entity type" == info.value.message
