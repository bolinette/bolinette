"""Entities, repositories, services and transactions against in-memory SQLite databases."""

from pathlib import Path
from typing import ClassVar, override

import pytest
from escondite import Cache
from muotti.errors import SourceNotFoundError, ValidationError
from pydantic import BaseModel
from soupape import AsyncInjector
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.core.exceptions import InitError
from bolinette.data import Database, database_system
from bolinette.data.exceptions import DatabaseError, DataError, EntityError, EntityNotFoundError
from bolinette.data.relational import (
    AbstractDatabase,
    AsyncRelationalDatabase,
    AsyncTransaction,
    EntityManager,
    RelationalDatabase,
    RelationalSystem,
    Repository,
    Service,
    declarative_base,
    repository,
    service,
)
from tests.data.conftest import AppFactory


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int | None]


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str]


class UserRepository(Repository[User]):
    async def by_name(self, name: str) -> User:
        return await self.first(select(User).where(User.name == name))


class UserService(Service[User]):
    pass


class OtherUserRepository(Repository[User]):
    pass


class OtherUserService(Service[User]):
    pass


class DerivedUserRepository(UserRepository):
    pass


class DerivedUserService(UserService):
    pass


class UserPayload(BaseModel):
    name: str
    age: int | None = None


class UserPatch(BaseModel):
    name: str | None = None
    age: int | None = None


class NotARepository:
    pass


class SpyDatabase(AbstractDatabase):
    disposed: ClassVar[list[str]] = []

    @override
    async def create_all(self) -> None:
        pass

    @override
    async def dispose(self) -> None:
        SpyDatabase.disposed.append(self.name)


class SpySystem(RelationalSystem):
    scheme = "spy://"
    python_package = "sqlalchemy"
    database = SpyDatabase


class FlatDatabase:
    def __init__(self, name: str, url: str, echo: bool) -> None:
        self.name = name
        self.url = url
        self.echo = echo
        self.in_memory = False

    async def create_all(self) -> None:
        pass

    async def dispose(self) -> None:
        pass


class NotRelationalSystem:
    scheme = "flat://"
    python_package = "sqlalchemy"

    def create(self, name: str, url: str, echo: bool) -> Database:
        return FlatDatabase(name, url, echo)


class OtherBase(DeclarativeBase):
    pass


class Orphan(OtherBase):
    __tablename__ = "orphans"

    id: Mapped[int] = mapped_column(primary_key=True)


class OrphanRepository(Repository[Orphan]):
    pass


def _register(cache: Cache) -> None:
    declarative_base("default", cache=cache)(Base)
    repository(cache=cache)(UserRepository)
    service(cache=cache)(UserService)


class TestEntityManager:
    async def test_entities_and_engines(self, make_app: AppFactory, cache: Cache) -> None:
        """Every mapped class of a registered base is an entity bound to the base's engine."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            entities = await scope.require(EntityManager)

        assert {e.origin for e in entities.entities} == {User, Tag}
        assert entities.is_entity_type(User)
        assert not entities.is_entity_type(Orphan)
        engine = entities.get_engine(User)
        assert isinstance(engine, AsyncRelationalDatabase)
        assert engine.name == "default"
        assert engine.in_memory
        assert engine.bases == [Base]
        assert entities.engines == {"default": engine}
        assert entities.get_engine_by_name("default") is engine

    async def test_unregistered_entity_has_no_engine(self, make_app: AppFactory, cache: Cache) -> None:
        """Asking the engine of a class outside the registered bases is an error."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            entities = await scope.require(EntityManager)

        with pytest.raises(EntityError, match="not registered"):
            entities.get_engine(Orphan)

    async def test_memory_url_forms(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """Both the bare and the `:memory:` SQLite url forms are recognised as in-memory databases."""
        _register(cache)
        (env_folder / "env.toml").write_text(
            '[[data.databases]]\nname = "default"\nurl = "sqlite+aiosqlite:///:memory:"\n'
        )
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            engine = (await scope.require(EntityManager)).get_engine(User)
            assert engine.in_memory
        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(Service[User])
            svc.create(UserPayload(name="Bob"))

    async def test_sync_database(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """A plain `sqlite://` url gives a synchronous engine wrapped for async use."""
        _register(cache)
        (env_folder / "env.toml").write_text('[[data.databases]]\nname = "default"\nurl = "sqlite://"\n')
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            entities = await scope.require(EntityManager)
            assert isinstance(entities.get_engine(User), RelationalDatabase)
        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(Service[User])
            svc.create(UserPayload(name="Bob"))
        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(Service[User])
            assert [u.name for u in await svc.get_all()] == ["Bob"]

    async def test_connection_must_be_relational(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """A base bound to a connection whose system is not a relational database is rejected."""
        declarative_base("default", cache=cache)(Base)
        database_system(cache=cache)(NotRelationalSystem)
        (env_folder / "env.toml").write_text('[[data.databases]]\nname = "default"\nurl = "flat://x"\n')
        blnt = await make_app()

        with pytest.raises(EntityError, match="is not a relational system"):
            async with blnt.injector.get_scoped_injector() as scope:
                await scope.require(EntityManager)

    async def test_engines_are_disposed_on_app_dispose(
        self, make_app: AppFactory, cache: Cache, env_folder: Path
    ) -> None:
        """Disposing a started application disposes every engine."""
        SpyDatabase.disposed.clear()
        declarative_base("default", cache=cache)(Base)
        database_system(cache=cache)(SpySystem)
        (env_folder / "env.toml").write_text('[[data.databases]]\nname = "default"\nurl = "spy://x"\n')
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            engine = (await scope.require(EntityManager)).get_engine(User)
        assert (engine.bases, engine.url, engine.echo, engine.in_memory) == ([Base], "spy://x", False, False)

        await blnt.dispose()

        assert SpyDatabase.disposed == ["default"]

    async def test_single_repository_per_entity(self, make_app: AppFactory, cache: Cache) -> None:
        """Two repositories registered for the same entity are rejected, naming both classes."""
        _register(cache)
        repository(cache=cache)(OtherUserRepository)

        with pytest.raises(InitError, match=r"already has repository \w+, only one") as info:
            await make_app()
        assert "UserRepository" in str(info.value)
        assert "OtherUserRepository" in str(info.value)

    async def test_single_service_per_entity(self, make_app: AppFactory, cache: Cache) -> None:
        """Two services registered for the same entity are rejected, naming both classes."""
        _register(cache)
        service(cache=cache)(OtherUserService)

        with pytest.raises(InitError, match=r"already has service \w+, only one") as info:
            await make_app()
        assert "UserService" in str(info.value)
        assert "OtherUserService" in str(info.value)

    async def test_repository_and_service_can_be_indirect_subclasses(self, make_app: AppFactory, cache: Cache) -> None:
        declarative_base("default", cache=cache)(Base)
        repository(cache=cache)(DerivedUserRepository)
        service(cache=cache)(DerivedUserService)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(Repository[User])
            svc = await scope.require(Service[User])

        assert isinstance(repo, DerivedUserRepository)
        assert isinstance(svc, DerivedUserService)
        assert repo.entity is User
        assert svc.entity is User

    async def test_repository_must_inherit_generic(self, make_app: AppFactory, cache: Cache) -> None:
        """A class registered as repository must inherit from `Repository[Entity]`."""
        declarative_base("default", cache=cache)(Base)
        repository(cache=cache)(NotARepository)  # pyright: ignore[reportArgumentType]

        with pytest.raises(InitError, match="must inherit from Repository"):
            await make_app()

    async def test_repository_entity_must_be_registered(self, make_app: AppFactory, cache: Cache) -> None:
        """A repository for an entity of an unregistered base is rejected."""
        declarative_base("default", cache=cache)(Base)
        repository(cache=cache)(OrphanRepository)

        with pytest.raises(InitError, match="is not a registered entity type"):
            await make_app()


class TestRepository:
    async def test_custom_repository_serves_the_generic_interface(self, make_app: AppFactory, cache: Cache) -> None:
        """A registered repository subclass is injected for both its own type and `Repository[Entity]`."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            generic = await scope.require(Repository[User])
            custom = await scope.require(UserRepository)

        assert isinstance(generic, UserRepository)
        assert generic is custom
        assert generic.entity is User
        assert [c.name for c in generic.primary_key] == ["id"]

    async def test_default_repository_for_other_entities(self, make_app: AppFactory, cache: Cache) -> None:
        """Entities without a custom repository get the generic one."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(Repository[Tag])

        assert type(repo) is Repository

    async def test_add_query_and_delete(self, make_app: AppFactory, cache: Cache) -> None:
        """Rows added in a scope are committed when it closes and can be queried, then deleted."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            repo.add(User(name="Bob", age=3))
            repo.add(User(name="Ann", age=5))
        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            assert (await repo.by_name("Ann")).age == 5
            assert (await repo.get_by_primary(1)).name == "Bob"
            assert await repo.first(select(User).where(User.name == "Zed"), raises=False) is None
            assert await repo.get_by_primary(99, raises=False) is None
            await repo.delete(await repo.get_by_primary(1))
        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            assert [u.name async for u in repo.find_all()] == ["Ann"]

    async def test_flush_populates_generated_keys(self, make_app: AppFactory, cache: Cache) -> None:
        """Flushing sends pending changes and fills generated keys while the transaction stays open."""
        _register(cache)
        blnt = await make_app()

        with pytest.raises(RuntimeError):  # noqa: PT012  the raise must happen inside the scope
            async with blnt.injector.get_scoped_injector() as scope:
                repo = await scope.require(UserRepository)
                user = User(name="Bob")
                repo.add(user)
                await repo.flush()
                assert user.id == 1
                raise RuntimeError("abort")
        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            assert [u async for u in repo.find_all()] == []

    async def test_transaction_commit_is_explicit(self, make_app: AppFactory, cache: Cache) -> None:
        """Committing the transaction by hand keeps the changes when the scope later fails."""
        _register(cache)
        blnt = await make_app()

        with pytest.raises(RuntimeError):  # noqa: PT012  the raise must happen inside the scope
            async with blnt.injector.get_scoped_injector() as scope:
                repo = await scope.require(UserRepository)
                transaction = await scope.require(AsyncTransaction)
                repo.add(User(name="Bob"))
                await transaction.commit()
                repo.add(User(name="Ann"))
                raise RuntimeError("abort")
        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            assert [u.name async for u in repo.find_all()] == ["Bob"]

    async def test_first_takes_the_first_of_several_rows(self, make_app: AppFactory, cache: Cache) -> None:
        """`first` returns the first matching row instead of failing when several match."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            repo.add(User(name="Bob", age=1))
            repo.add(User(name="Bob", age=2))
        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            first = await repo.first(select(User).where(User.name == "Bob").order_by(User.age))
            assert first.age == 1

    async def test_missing_entity_raises(self, make_app: AppFactory, cache: Cache) -> None:
        """Looking up a missing row with the default `raises=True` is an `EntityNotFoundError`."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            with pytest.raises(EntityNotFoundError) as info:
                await repo.get_by_primary(1)

        assert info.value.entity is User

    async def test_primary_key_arity(self, make_app: AppFactory, cache: Cache) -> None:
        """The number of primary key values must match the key columns."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            with pytest.raises(DataError, match="has 1 columns, but 2 values"):
                await repo.get_by_primary(1, 2)


class TestService:
    async def test_custom_service_serves_the_generic_interface(self, make_app: AppFactory, cache: Cache) -> None:
        """A registered service subclass is injected for both its own type and `Service[Entity]`."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            generic = await scope.require(Service[User])
            custom = await scope.require(UserService)
            assert generic is custom
            assert generic.entity is User
            assert isinstance(generic.repository, UserRepository)
            assert type(await scope.require(Service[Tag])) is Service

    async def test_create_maps_the_payload(self, make_app: AppFactory, cache: Cache) -> None:
        """`create` maps a payload to a new entity and adds it to the repository."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            user = svc.create(UserPayload(name="Bob", age=3))
            assert (user.name, user.age, user.id) == ("Bob", 3, None)
        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            assert [(u.id, u.name) for u in await svc.get_all()] == [(1, "Bob")]

    async def test_create_from_dict(self, make_app: AppFactory, cache: Cache) -> None:
        """A plain dictionary is also a valid payload."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            assert svc.create({"name": "Ann"}).name == "Ann"

    async def test_create_rejects_missing_required_column(self, make_app: AppFactory, cache: Cache) -> None:
        """A payload leaving a non-nullable column unset is rejected by the mapper before any insert."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            with pytest.raises(SourceNotFoundError, match=r"User\.name"):
                svc.create(UserPatch(age=3))

    async def test_create_with_validation_collects_errors(self, make_app: AppFactory, cache: Cache) -> None:
        """With `validate=True` mapping errors are collected into a `ValidationError`."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            with pytest.raises(ValidationError):
                svc.create({"name": "Bob", "age": "old"}, validate=True)

    async def test_update_merges_present_fields(self, make_app: AppFactory, cache: Cache) -> None:
        """`update` merges the set payload fields into the entity and keeps the others."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            svc.create(UserPayload(name="Bob", age=3))
        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            user = await svc.get_by_primary(1)
            svc.update(user, UserPatch(name="Bobby"))
            assert (user.name, user.age) == ("Bobby", 3)
        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            assert (await svc.get_by_primary(1)).name == "Bobby"

    async def test_get_by_primary_without_raising(self, make_app: AppFactory, cache: Cache) -> None:
        """`raises=False` returns `None` for a missing row."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            assert await svc.get_by_primary(1, raises=False) is None
            with pytest.raises(EntityNotFoundError):
                await svc.get_by_primary(1)

    async def test_delete(self, make_app: AppFactory, cache: Cache) -> None:
        """`delete` removes the entity and returns it."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            svc.create(UserPayload(name="Bob"))
        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            user = await svc.get_by_primary(1)
            assert await svc.delete(user) is user
        async with blnt.injector.get_scoped_injector() as scope:
            svc = await scope.require(UserService)
            assert await svc.get_all() == []


class TestTransaction:
    async def test_exception_rolls_back(self, make_app: AppFactory, cache: Cache) -> None:
        """An exception escaping the scope rolls back the pending changes."""
        _register(cache)
        blnt = await make_app()

        with pytest.raises(RuntimeError):  # noqa: PT012  the raise must happen inside the scope
            async with blnt.injector.get_scoped_injector() as scope:
                repo = await scope.require(UserRepository)
                repo.add(User(name="Bob"))
                raise RuntimeError("abort")
        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            assert [u async for u in repo.find_all()] == []

    async def test_failed_commit_rolls_back_and_raises(self, make_app: AppFactory, cache: Cache) -> None:
        """A commit rejected by the database rolls back and the error reaches the caller."""
        _register(cache)
        blnt = await make_app()

        with pytest.raises(IntegrityError):  # noqa: PT012  the scope must close to flush
            async with blnt.injector.get_scoped_injector() as scope:
                repo = await scope.require(UserRepository)
                repo.add(User(id=1, name="Bob"))
                repo.add(User(id=1, name="Ann"))
        async with blnt.injector.get_scoped_injector() as scope:
            repo = await scope.require(UserRepository)
            assert [u async for u in repo.find_all()] == []

    async def test_sessions_open_lazily_by_connection(self, make_app: AppFactory, cache: Cache) -> None:
        """A session is opened on the first `get` of a connection name and reused afterwards."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            transaction = await scope.require(AsyncTransaction)
            assert "default" not in transaction
            session = transaction.get("default")
            assert "default" in transaction
            assert transaction.get("default") is session

    async def test_unknown_connection_has_no_session(self, make_app: AppFactory, cache: Cache) -> None:
        """Asking a session for a connection without a relational engine is an error."""
        _register(cache)
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            transaction = await scope.require(AsyncTransaction)
            with pytest.raises(DatabaseError, match="No relational engine"):
                transaction.get("other")
            assert "other" not in transaction

    async def test_scope_is_the_unit_of_work(self, make_app: AppFactory, cache: Cache) -> None:
        """The injector enters the transaction when building it and exits it with the scope."""
        _register(cache)
        blnt = await make_app()
        entered: list[str] = []
        original = AsyncTransaction.__aenter__

        async def spy(self: AsyncTransaction) -> AsyncTransaction:
            entered.append("enter")
            return await original(self)

        AsyncTransaction.__aenter__ = spy
        try:
            async with blnt.injector.get_scoped_injector() as scope:
                await scope.require(AsyncTransaction)
        finally:
            AsyncTransaction.__aenter__ = original

        assert entered == ["enter"]

    async def test_transaction_is_scoped(self, make_app: AppFactory, cache: Cache) -> None:
        """Each scope gets its own transaction."""
        _register(cache)
        blnt = await make_app()

        injector: AsyncInjector = blnt.injector
        async with injector.get_scoped_injector() as first, injector.get_scoped_injector() as second:
            t1 = await first.require(AsyncTransaction)
            t2 = await second.require(AsyncTransaction)
            assert t1 is not t2
            assert t1 is await first.require(AsyncTransaction)
