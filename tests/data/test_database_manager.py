import pytest

from bolinette.core import Cache
from bolinette.core.logging import Logger
from bolinette.core.testing import Mock
from bolinette.data import DatabaseManager, DataSection, database_system
from bolinette.data.exceptions import DatabaseError
from bolinette.data.objects import DatabaseSection
from bolinette.data.relational import AsyncRelationalDatabase


def test_init_systems() -> None:
    cache = Cache()

    class _SQLite:
        scheme = "sqlite+aiosqlite://"
        python_package = "aiosqlite"
        manager = AsyncRelationalDatabase

    database_system(cache=cache)(_SQLite)
    mock = Mock(cache=cache)
    mock.mock(DataSection).setup(lambda s: s.databases, [])
    mock.mock(Logger[DatabaseManager])
    mock.injection.add_singleton(DatabaseManager)

    manager = mock.injection.require(DatabaseManager)

    assert manager.has_system("sqlite+aiosqlite://")
    assert not manager.has_system("some-scheme://")

    system = manager.get_system("sqlite+aiosqlite://")
    assert system.scheme == "sqlite+aiosqlite://"
    assert system.python_package == "aiosqlite"
    assert system.manager is AsyncRelationalDatabase


def test_fail_init_systems_no_system() -> None:
    mock = Mock(cache=Cache())
    mock.mock(DataSection).setup(lambda s: s.databases, [])
    mock.mock(Logger[DatabaseManager])
    mock.injection.add_singleton(DatabaseManager)

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert "No system was registered with @database_system" == info.value.message


def test_fail_init_systems_python_package_not_found() -> None:
    cache = Cache()

    class _SQLite:
        scheme = "sqlite+aiosqlite://"
        python_package = "some-package"
        manager = AsyncRelationalDatabase

    database_system(cache=cache)(_SQLite)
    mock = Mock(cache=cache)
    mock.mock(DataSection).setup(lambda s: s.databases, [])
    mock.mock(Logger[DatabaseManager])
    mock.injection.add_singleton(DatabaseManager)

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert "Database system 'sqlite+aiosqlite://', Python package 'some-package' was not found" == info.value.message


class SQLite:
    scheme = "sqlite+aiosqlite://"
    python_package = "aiosqlite"
    manager = AsyncRelationalDatabase


def test_init_connections() -> None:
    cache = Cache()
    database_system(cache=cache)(SQLite)

    def get_sections() -> list[DatabaseSection]:
        return [DatabaseSection(name="test-connection", url="sqlite+aiosqlite://", echo=False)]

    mock = Mock(cache=cache)
    mock.mock(DataSection).setup(lambda s: s.databases, get_sections())
    mock.mock(Logger[DatabaseManager]).dummy()
    mock.injection.add_singleton(DatabaseManager)

    manager = mock.injection.require(DatabaseManager)

    assert manager.has_connection("test-connection")
    assert not manager.has_connection("some-connection")

    conn = manager.get_connection("test-connection")
    assert conn.name == "test-connection"
    assert conn.url == "sqlite+aiosqlite://"
    assert conn.echo is False
    assert conn.manager is AsyncRelationalDatabase


def test_fail_init_connections_invalid_url() -> None:
    cache = Cache()
    database_system(cache=cache)(SQLite)

    def get_sections() -> list[DatabaseSection]:
        return [DatabaseSection(name="test-connection", url="invalid url!", echo=False)]

    mock = Mock(cache=cache)
    mock.mock(DataSection).setup(lambda s: s.databases, get_sections())
    mock.mock(Logger[DatabaseManager])
    mock.injection.add_singleton(DatabaseManager)

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert "Database connection 'test-connection', Invalid URL 'invalid url!'" == info.value.message


def test_fail_init_connections_system_not_found() -> None:
    cache = Cache()
    database_system(cache=cache)(SQLite)

    def get_sections() -> list[DatabaseSection]:
        return [DatabaseSection(name="test-connection", url="protocol://", echo=False)]

    mock = Mock(cache=cache)
    mock.mock(DataSection).setup(lambda s: s.databases, get_sections())
    mock.mock(Logger[DatabaseManager])
    mock.injection.add_singleton(DatabaseManager)

    with pytest.raises(DatabaseError) as info:
        mock.injection.require(DatabaseManager)

    assert (
        "Database connection 'test-connection', Database system supporting scheme 'protocol://' was not found"
        == info.value.message
    )
