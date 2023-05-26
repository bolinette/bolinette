import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from bolinette import Cache, meta
from bolinette.ext.data.exceptions import DataError, EntityNotFoundError
from bolinette.ext.data.relational import Repository, entity, get_base, repository
from bolinette.ext.data.relational.repository import _RepositoryMeta
from bolinette.testing import Mock


def setup_test():
    cache = Cache()

    @entity(entity_key="id", cache=cache)
    class Entity(get_base("tests", cache=cache)):
        __tablename__ = "entities"
        id: Mapped[int] = mapped_column(primary_key=True)

    return cache, Entity


def test_init_repo() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    mock.mock(AsyncSession)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    assert list(repo._primary_key) == [Entity.id]


async def test_iterate() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    e1 = Entity()
    e2 = Entity()

    class _MockedResult:
        def scalars(self):
            return [e1, e2]

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    res = []
    async for e in repo.iterate(select(Entity)):
        res.append(e)

    assert res == [e1, e2]


async def test_find_all() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    e1 = Entity()
    e2 = Entity()

    class _MockedResult:
        def scalars(self):
            return [e1, e2]

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    res = []
    async for e in repo.find_all():
        res.append(e)

    assert res == [e1, e2]


async def test_first() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    e1 = Entity()

    class _MockedResult:
        def scalar_one_or_none(self):
            return e1

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    res = await repo.first(select(Entity))

    assert res == e1


async def test_first_none() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    res = await repo.first(select(Entity), raises=False)

    assert res is None


async def test_fail_first_none() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(EntityNotFoundError) as info:
        await repo.first(select(Entity))

    assert f"Entity {Entity} not found" == info.value.message


async def test_get_by_primary() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    e1 = Entity()

    class _MockedResult:
        def scalar_one_or_none(self):
            return e1

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    res = await repo.get_by_primary(1)

    assert res == e1


async def test_get_by_primary_none() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    res = await repo.get_by_primary(1, raises=False)

    assert res is None


async def test_fail_get_by_primary_none() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(EntityNotFoundError) as info:
        await repo.get_by_primary(1)

    assert f"Entity {Entity} not found" == info.value.message


async def test_fail_get_by_primary_values_mismatch() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    mock.mock(AsyncSession)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(DataError) as info:
        await repo.get_by_primary(1, "test")

    assert f"Primary key of {Entity} has 1 columns, but 2 values were provided" == info.value.message


async def test_get_by_key() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    e1 = Entity()

    class _MockedResult:
        def scalar_one_or_none(self):
            return e1

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    res = await repo.get_by_key(1)

    assert res == e1


async def test_get_by_key_none() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    res = await repo.get_by_key(1, raises=False)

    assert res is None


async def test_fail_get_by_key_none() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    class _MockedResult:
        def scalar_one_or_none(self):
            return None

    async def _execute(*_):
        return _MockedResult()

    mock.mock(AsyncSession).setup("execute", _execute)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(EntityNotFoundError) as info:
        await repo.get_by_key(1)

    assert f"Entity {Entity} not found" == info.value.message


async def test_fail_get_by_key_values_mismatch() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    mock.mock(AsyncSession)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(DataError) as info:
        await repo.get_by_key(1, "test")

    assert f"Entity key of {Entity} has 1 columns, but 2 values were provided" == info.value.message


async def test_add() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    e1 = Entity()
    entities = []

    def _add(entity):
        entities.append(entity)

    mock.mock(AsyncSession).setup("add", _add)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    repo.add(e1)

    assert entities == [e1]


async def test_delete() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    e1 = Entity()
    entities = [e1]

    async def _delete(entity):
        entities.remove(entity)

    mock.mock(AsyncSession).setup("delete", _delete)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    await repo.delete(e1)

    assert entities == []


async def test_commit() -> None:
    cache, Entity = setup_test()
    mock = Mock(cache=cache)

    commit = False

    async def _commit():
        nonlocal commit
        commit = True

    mock.mock(AsyncSession).setup("commit", _commit)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    await repo.commit()

    assert commit is True


def test_custom_repo() -> None:
    cache, Entity = setup_test()
    cache = Cache()

    @repository(Entity, cache=cache)
    class _EntityRepo(Repository[Entity]):
        pass

    res = cache.get(_RepositoryMeta)
    assert res == [_EntityRepo]
    assert meta.get(res[0], _RepositoryMeta).entity is Entity
