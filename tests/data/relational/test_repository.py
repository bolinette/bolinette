from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from bolinette import Cache, meta
from bolinette.ext.data.exceptions import DataError, EntityNotFoundError
from bolinette.ext.data.relational import Repository, get_base, repository, entity
from bolinette.ext.data.relational.repository import _RepositoryMeta
from bolinette.inject import ArgResolverOptions, injection_arg_resolver
from bolinette.testing import Mock


test_cache = Cache()


@entity(cache=test_cache)
class Entity(get_base("tests", cache=test_cache)):
    __tablename__ = "entities"
    id: Mapped[int] = mapped_column(primary_key=True)


@injection_arg_resolver(cache=test_cache)
class EntityArgResolver:
    def supports(self, options: ArgResolverOptions) -> bool:
        return options.cls is type and options.type_vars == (Entity,)

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        return options.name, Entity


def test_init_repo() -> None:
    mock = Mock(cache=test_cache)

    mock.mock(AsyncSession)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    assert list(repo._primary_key) == [Entity.id]


async def test_iterate() -> None:
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

    mock.mock(AsyncSession)
    mock.injection.add(Repository[Entity], "singleton")

    repo = mock.injection.require(Repository[Entity])

    with pytest.raises(DataError) as info:
        await repo.get_by_primary(1, "test")

    assert f"Primary key of {Entity} has 1 columns, but 2 values were provided" == info.value.message


async def test_add() -> None:
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    mock = Mock(cache=test_cache)

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
    cache = Cache()

    @repository(Entity, cache=cache)
    class _EntityRepo(Repository[Entity]):
        pass

    res = cache.get(_RepositoryMeta)
    assert res == [_EntityRepo]
    assert meta.get(res[0], _RepositoryMeta).entity is Entity
