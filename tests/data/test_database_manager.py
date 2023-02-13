from typing import Annotated

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase
import pytest

from bolinette.testing import Mock
from bolinette import Cache
from bolinette.ext.data import PrimaryKey
from bolinette.ext.data.exceptions import DatabaseError
from bolinette.ext.data.database import RelationalDatabase
from bolinette.ext.data.objects import DataSection, _DatabaseSection
from bolinette.ext.data.manager import (
    DatabaseManager,
    EntityManager,
    TableDefinition,
    TableColumn,
    database_system,
    PrimaryKeyConstraint,
)


def _setup_test(cache: Cache, env: DataSection) -> Mock:
    mock = Mock(cache=cache)
    mock.injection.add(DataSection, "singleton", instance=env)
    mock.mock(EntityManager)
    mock.injection.add(DatabaseManager, "singleton")
    return mock

class SQLite:
    scheme = "sqlite+aiosqlite://"
    python_package = "aiosqlite"
    manager = RelationalDatabase


def create_env_section(name: str = "default", url: str = "sqlite+aiosqlite://") -> DataSection:
    db = _DatabaseSection()
    db.echo = True
    db.name = name
    db.url = url
    env = DataSection()
    env.databases = [db]
    return env


def test_init_db_engines() -> None:
    cache = Cache()

    database_system(cache=cache)(SQLite)

    class _User:
        id: Annotated[int, PrimaryKey()]
        name: str

    def _get_entities() -> dict[type, TableDefinition]:
        user_table = TableDefinition("user", _User, "default")
        user_table.columns["id"] = TableColumn(user_table, "id", int, Integer, False, None)
        user_table.columns["name"] = TableColumn(user_table, "name", str, String, False, None)
        user_table.constraints["user_pk"] = PrimaryKeyConstraint(user_table, "user_pk", [user_table.columns["id"]])
        return {_User: user_table}

    mock = _setup_test(cache, create_env_section())
    mock.mock(EntityManager).setup("definitions", _get_entities())

    manager = mock.injection.require(DatabaseManager)

    engine = manager.get_engine("default")
    assert isinstance(engine, RelationalDatabase)

    definition = engine.get_definition(_User)
    assert issubclass(definition, DeclarativeBase)


def test_fail_no_db_system_registered() -> None:
    mock = _setup_test(Cache(), create_env_section())

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert "No system was registered with @database_system" == info.value.message


def test_fail_env_db_url_unknown() -> None:
    cache = Cache()

    database_system(cache=cache)(SQLite)

    mock = _setup_test(cache, create_env_section("some-db", "invalid url"))

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert (
        "Database connection 'some-db': Invalid URL 'invalid url'"
        == info.value.message
    )


def test_fail_unsupported_scheme() -> None:
    cache = Cache()

    @database_system(cache=cache)
    class SQLite:
        scheme = "sqlite+aiosqlite://"
        python_package = "aiosqlite"
        manager = RelationalDatabase

    mock = _setup_test(cache, create_env_section("some-db", "some-protocol://some-user:some-pwd@some-url:1234"))

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert (
        "Database connection 'some-db', Database system supporting scheme 'some-protocol://' was not found"
        == info.value.message
    )


def test_fail_python_package_not_found() -> None:
    cache = Cache()

    @database_system(cache=cache)
    class SQLite:
        scheme = "sqlite+aiosqlite://"
        python_package = "some-python-package"
        manager = RelationalDatabase

    mock = _setup_test(cache, create_env_section())

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert (
        "Database system 'sqlite+aiosqlite://', Python package 'some-python-package' was not found"
        == info.value.message
    )


def test_fail_database_connection_not_found() -> None:
    cache = Cache()

    database_system(cache=cache)(SQLite)

    class _User:
        pass

    def _get_entities() -> dict[type, TableDefinition]:
        user_table = TableDefinition("user", _User, "some-db")
        return {_User: user_table}

    mock = _setup_test(cache, create_env_section())
    mock.mock(EntityManager).setup("definitions", _get_entities())

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert (
        f"Entity {_User}, No 'some-db' database is registered in environment"
        == info.value.message
    )
