"""The data extension: registered services, startup behaviour, commands and scaffolding hooks."""

from pathlib import Path

import pytest
from escondite import Cache
from peritype import wrap_type
from soupape import ServiceCollection
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.core import CoreExtension, startup
from bolinette.core.mapping import Mapper
from bolinette.data import DatabaseManager, DataExtension, SqlAlchemyProtocol
from bolinette.data.relational import AsyncTransaction, EntityManager, Repository, Service, declarative_base
from tests.data.conftest import AppFactory


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str]


class TestRegistration:
    async def test_depends_on_core(self, make_app: AppFactory) -> None:
        """The data extension is loaded after core."""
        blnt = await make_app()

        assert [type(ext) for ext in blnt.extensions] == [CoreExtension, DataExtension]

    async def test_services_are_registered(self, make_app: AppFactory, cache: Cache) -> None:
        """Managers, the transaction and the entity repositories and services are injectable."""
        declarative_base("default", cache=cache)(Base)
        services = ServiceCollection()

        await make_app(services=services)

        assert services.is_registered(DatabaseManager)
        assert services.is_registered(EntityManager)
        assert services.is_registered(AsyncTransaction)
        assert services.is_registered(Repository[Item])
        assert services.is_registered(Service[Item])

    async def test_mapping_protocol_is_registered(self, make_app: AppFactory, cache: Cache) -> None:
        """The SQLAlchemy mapping protocol handles declarative classes in the application mapper."""
        seen: list[Mapper] = []

        @startup(cache=cache)
        async def init(mapper: Mapper) -> None:
            seen.append(mapper)

        await make_app()

        assert isinstance(seen[0].registry.resolve(wrap_type(Item)), SqlAlchemyProtocol)

    async def test_startup_creates_tables_for_memory_databases(self, make_app: AppFactory, cache: Cache) -> None:
        """Tables of in-memory databases are created on startup, so entities can be stored right away."""
        declarative_base("default", cache=cache)(Base)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(Repository[Item])
            repo.add(Item(label="a"))
        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(Repository[Item])
            assert [i.label async for i in repo.find_all()] == ["a"]

    async def test_db_init_command_creates_tables(
        self, make_app: AppFactory, cache: Cache, env_folder: Path, tmp_cwd: Path
    ) -> None:
        """`db init` creates the tables of every configured database, here a file-based SQLite one."""
        declarative_base("default", cache=cache)(Base)
        (env_folder / "env.toml").write_text(
            f'[[data.databases]]\nname = "default"\nurl = "sqlite:///{tmp_cwd}/db.sqlite"\n'
        )
        blnt = await make_app(start=False)

        assert await blnt.run_command(["db", "init"]) is None

        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(Repository[Item])
            assert [i async for i in repo.find_all()] == []


class TestScaffolding:
    async def test_new_project_hooks(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """Scaffolding with the data extension adds the entity packages and a local database config."""
        blnt = await make_app(start=False)

        await blnt.run_command(["new", "project", "myapp", "-e", "data"])

        for name in ("entities", "repositories", "services"):
            assert (tmp_cwd / "myapp" / name / "__init__.py").exists()
        local = (tmp_cwd / "env" / "env.local.development.toml").read_text()
        assert "[[data.databases]]" in local
        assert 'url = "sqlite+aiosqlite://"' in local
        assert "from bolinette.data import DataExtension" in (tmp_cwd / "myapp" / "app.py").read_text()
        assert '"bolinette-data",' in (tmp_cwd / "pyproject.toml").read_text()

    def test_hooks_are_declared_in_order(self) -> None:
        """The extension lists its two scaffolding hooks."""
        names = [hook.__name__ for hook in DataExtension().get_new_project_hooks()]

        assert names == ["create_data_packages", "create_database_config"]


class TestFailures:
    async def test_missing_connection_for_base(self, make_app: AppFactory, cache: Cache) -> None:
        """A declarative base bound to an unknown connection fails when the entities are first needed."""
        declarative_base("other", cache=cache)(Base)
        blnt = await make_app()

        with pytest.raises(Exception, match="No 'other' database connection"):
            async with blnt.injector.get_scoped_injector() as scope:
                await scope.require(EntityManager)
