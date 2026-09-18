"""Configuration section and database manager: systems, connections and their errors."""

import logging
from pathlib import Path
from typing import cast

import pytest
from escondite import Cache
from soupape import AsyncInjector, ServiceCollection

from bolinette.core import Logger, startup
from bolinette.core.configuration import ConfigSection
from bolinette.data import Database, DatabaseManager, DatabaseSection, DataSection, database_system
from bolinette.data.defaults import AsyncPostgreSQL, AsyncSQLite, PostgreSQL, SQLite
from bolinette.data.exceptions import DatabaseError
from bolinette.data.relational import AsyncRelationalDatabase, RelationalDatabase, _database
from tests.data.conftest import AppFactory


class FakeSystem:
    scheme = "fake://"
    python_package = "nope_driver_package"

    def create(self, name: str, url: str, echo: bool) -> Database:
        return RelationalDatabase(name, url, echo, [])


class TestSection:
    def test_defaults(self) -> None:
        """The data section defaults to no database."""
        assert DataSection().databases == []

    def test_database_section(self) -> None:
        """A database entry needs a name and a url, echo is off by default."""
        section = DatabaseSection(name="default", url="sqlite://")

        assert section.echo is False


class TestDatabaseManager:
    @staticmethod
    async def _manager(make_app: AppFactory, cache: Cache) -> DatabaseManager:
        seen: list[DatabaseManager] = []

        @startup(cache=cache)
        async def init(databases: DatabaseManager) -> None:
            seen.append(databases)

        await make_app()
        return seen[0]

    async def test_default_systems(self, make_app: AppFactory, cache: Cache) -> None:
        """The four bundled systems are registered, sorted by scheme."""
        manager = await self._manager(make_app, cache)

        assert [s.scheme for s in manager.systems] == [
            "postgresql+asyncpg://",
            "postgresql://",
            "sqlite+aiosqlite://",
            "sqlite://",
        ]
        assert manager.has_system("sqlite://")
        assert isinstance(manager.get_system("sqlite+aiosqlite://"), AsyncSQLite)
        assert not manager.has_system("mysql://")

    async def test_databases_from_configuration(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """Each configured database is created by the system matching its url scheme."""
        (env_folder / "env.toml").write_text(
            '[[data.databases]]\nname = "default"\nurl = "sqlite+aiosqlite://"\n'
            '[[data.databases]]\nname = "sync"\nurl = "sqlite://"\necho = true\n'
        )
        manager = await self._manager(make_app, cache)

        assert [d.name for d in manager.databases] == ["default", "sync"]
        assert manager.has_database("sync")
        assert isinstance(manager.get_database("default"), AsyncRelationalDatabase)
        sync = manager.get_database("sync")
        assert isinstance(sync, RelationalDatabase)
        assert (sync.url, sync.echo) == ("sqlite://", True)

    async def test_unknown_database(self, make_app: AppFactory, cache: Cache) -> None:
        """Asking for a database name absent from the configuration is an error naming the connection."""
        manager = await self._manager(make_app, cache)

        assert not manager.has_database("other")
        with pytest.raises(DatabaseError, match=r"Database connection 'other'.*No database is defined"):
            manager.get_database("other")

    async def test_duplicate_database_name(self, make_app: AppFactory, env_folder: Path) -> None:
        """Two configured databases with the same name are rejected."""
        (env_folder / "env.toml").write_text(
            '[[data.databases]]\nname = "main"\nurl = "sqlite://"\n[[data.databases]]\nname = "main"\nurl = "sqlite://"\n'
        )

        with pytest.raises(DatabaseError, match=r"Database connection 'main'.*used twice"):
            await make_app()

    async def test_connection_log_hides_the_url(
        self, make_app: AppFactory, cache: Cache, env_folder: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The debug line for a connection names it and its scheme, never the url and its credentials."""
        (env_folder / "env.toml").write_text('[[data.databases]]\nname = "main"\nurl = "sqlite:///s3cret@host/db"\n')
        caplog.set_level(logging.DEBUG)

        await self._manager(make_app, cache)

        assert "Registered connection 'main' on sqlite://" in caplog.text
        assert "s3cret" not in caplog.text

    async def test_unknown_scheme(self, make_app: AppFactory, env_folder: Path) -> None:
        """A url whose scheme matches no system is reported with the connection name."""
        (env_folder / "env.toml").write_text('[[data.databases]]\nname = "main"\nurl = "mysql://host/db"\n')

        with pytest.raises(DatabaseError, match=r"Database connection 'main'.*scheme 'mysql:\/\/' was not found"):
            await make_app()

    async def test_invalid_url(self, make_app: AppFactory, env_folder: Path) -> None:
        """A url without a scheme is invalid."""
        (env_folder / "env.toml").write_text('[[data.databases]]\nname = "main"\nurl = "not-a-url"\n')

        with pytest.raises(DatabaseError, match="Invalid URL"):
            await make_app()

    async def test_missing_driver_package(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """A configured connection whose driver package is not installed is reported."""
        database_system(cache=cache)(FakeSystem)
        (env_folder / "env.toml").write_text('[[data.databases]]\nname = "main"\nurl = "fake://x"\n')

        with pytest.raises(DatabaseError, match="Python package 'nope_driver_package' was not found"):
            await make_app()

    async def test_unused_driver_is_not_imported(self, make_app: AppFactory, cache: Cache) -> None:
        """A system whose driver is missing is harmless as long as no connection uses it."""
        database_system(cache=cache)(FakeSystem)

        manager = await self._manager(make_app, cache)

        assert manager.has_system("fake://")

    async def test_no_system_registered(self) -> None:
        """A manager built without any registered system is a programming error."""
        services = ServiceCollection()
        services.add_singleton(Cache, lambda: Cache())
        services.add_singleton(ConfigSection[DataSection], lambda: ConfigSection(DataSection, "data", DataSection()))
        services.add_singleton(
            Logger[DatabaseManager], lambda: cast(Logger[DatabaseManager], logging.getLogger("test"))
        )
        services.add_singleton(DatabaseManager)

        with pytest.raises(DatabaseError, match="No database system was registered"):
            async with AsyncInjector(services) as injector:
                await injector.require(DatabaseManager)

    def test_bundled_systems_metadata(self) -> None:
        """Bundled systems name their scheme and driver package and create the matching database class."""
        assert (SQLite.scheme, SQLite.python_package) == ("sqlite://", "sqlalchemy")
        assert isinstance(SQLite(Cache()).create("s", "sqlite://", False), RelationalDatabase)
        assert isinstance(AsyncSQLite(Cache()).create("a", "sqlite+aiosqlite://", False), AsyncRelationalDatabase)

    def test_postgresql_systems(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The PostgreSQL systems create sync and async relational databases without a driver being installed."""

        def fake_engine(url: str, echo: bool) -> str:
            return url

        monkeypatch.setattr(_database, "create_engine", fake_engine)
        monkeypatch.setattr(_database, "create_async_engine", fake_engine)

        assert (PostgreSQL.scheme, AsyncPostgreSQL.scheme) == ("postgresql://", "postgresql+asyncpg://")
        assert isinstance(PostgreSQL(Cache()).create("p", "postgresql://h/db", False), RelationalDatabase)
        assert isinstance(
            AsyncPostgreSQL(Cache()).create("a", "postgresql+asyncpg://h/db", False), AsyncRelationalDatabase
        )
