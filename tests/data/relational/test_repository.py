# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.core import Cache, meta
from bolinette.core.testing import Mock
from bolinette.core.types import Type
from bolinette.data.exceptions import DataError, EntityNotFoundError
from bolinette.data.relational import EntitySession, Repository, declarative_base, entity, repository
from bolinette.data.relational.repository import RepositoryMeta


def test_init_repo() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    mock.mock(EntitySession[Entity])
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    assert list(repo.primary_key) == [Entity.id]


async def test_iterate() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    e1 = Entity()
    e2 = Entity()

    class _MockedResult:
        def scalars(self):
            return [e1, e2]

    async def _execute(*_: Any):
        return _MockedResult()

    mock.mock(EntitySession[Entity]).setup(lambda s: s.execute, _execute)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    res: list[Entity] = []
    async for e in repo.iterate(select(Entity)):
        res.append(e)

    assert res == [e1, e2]


async def test_find_all() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    e1 = Entity()
    e2 = Entity()

    class _MockedResult:
        def scalars(self):
            return [e1, e2]

    async def _execute(*_: Any):
        return _MockedResult()

    mock.mock(EntitySession[Entity]).setup(lambda s: s.execute, _execute)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    res: list[Entity] = []
    async for e in repo.find_all():
        res.append(e)

    assert res == [e1, e2]


async def test_first() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    e1 = Entity()

    class _MockedResult:
        def scalar_one_or_none(self) -> Entity:
            return e1

    async def _execute(*_: Any) -> _MockedResult:
        return _MockedResult()

    mock.mock(EntitySession[Entity]).setup(lambda s: s.execute, _execute)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    res = await repo.first(select(Entity))

    assert res == e1


async def test_first_none() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_: Any):
        return _MockedResult()

    mock.mock(EntitySession[Entity]).setup(lambda s: s.execute, _execute)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    res = await repo.first(select(Entity), raises=False)

    assert res is None


async def test_fail_first_none() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_: Any):
        return _MockedResult()

    mock.mock(EntitySession[Entity]).setup(lambda s: s.execute, _execute)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(EntityNotFoundError) as info:
        await repo.first(select(Entity))

    assert f"Entity {Entity} not found" == info.value.message


async def test_get_by_primary() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    e1 = Entity()

    class _MockedResult:
        def scalar_one_or_none(self):
            return e1

    async def _execute(*_: Any):
        return _MockedResult()

    mock.mock(EntitySession[Entity]).setup(lambda s: s.execute, _execute)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    res = await repo.get_by_primary(1)

    assert res == e1


async def test_get_by_primary_none() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_: Any):
        return _MockedResult()

    mock.mock(EntitySession[Entity]).setup(lambda s: s.execute, _execute)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    res = await repo.get_by_primary(1, raises=False)

    assert res is None


async def test_fail_get_by_primary_none() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_: Any):
        return _MockedResult()

    mock.mock(EntitySession[Entity]).setup(lambda s: s.execute, _execute)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(EntityNotFoundError) as info:
        await repo.get_by_primary(1)

    assert f"Entity {Entity} not found" == info.value.message


async def test_fail_get_by_primary_values_mismatch() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    mock.mock(EntitySession[Entity])
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(DataError) as info:
        await repo.get_by_primary(1, "test")

    assert f"Primary key of {Entity} has 1 columns, but 2 values were provided" == info.value.message


async def test_add() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    e1 = Entity()
    entities: list[Entity] = []

    def _add(entity: Entity) -> None:
        entities.append(entity)

    mock.mock(EntitySession[Entity]).setup(lambda s: s.add, _add)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    repo.add(e1)

    assert entities == [e1]


async def test_delete() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    e1 = Entity()
    entities = [e1]

    async def _delete(entity: Entity) -> None:
        entities.remove(entity)

    mock.mock(EntitySession[Entity]).setup(lambda s: s.delete, _delete)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    await repo.delete(e1)

    assert entities == []


async def test_commit() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    mock = Mock(cache=cache)

    commit = False

    async def _commit():
        nonlocal commit
        commit = True

    mock.mock(EntitySession[Entity]).setup(lambda s: s.commit, _commit)
    mock.injection.add_singleton(Repository[Entity])

    repo = mock.injection.require(Repository[Entity])

    await repo.commit()

    assert commit is True


def test_custom_repo() -> None:
    cache = Cache()

    @declarative_base("tests", cache=cache)
    class TestBase(DeclarativeBase):
        pass

    @entity(cache=cache)
    class Entity(TestBase):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    cache = Cache()

    @repository(cache=cache)
    class _EntityRepo(Repository[Entity]):
        pass

    res: list[RepositoryMeta[Any]] = cache.get(RepositoryMeta)
    assert res == [_EntityRepo]
    assert meta.get(res[0], RepositoryMeta).repo_t == Type(_EntityRepo)
    assert meta.get(res[0], RepositoryMeta).repo_t.bases[0] == Type(Repository[Entity])
