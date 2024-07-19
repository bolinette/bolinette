# pyright: reportUninitializedInstanceVariable=false
from typing import Any

import pytest
from sqlalchemy.orm import Mapped, mapped_column

from bolinette.core import Cache
from bolinette.core.mapping import Mapper
from bolinette.core.testing import Mock
from bolinette.data.exceptions import ColumnNotNullableError, WrongColumnTypeError
from bolinette.data.relational import Repository, Service, get_base


def test_create() -> None:
    cache = Cache()

    mock = Mock(cache=cache)

    class _Entity(get_base("tests", cache=cache)):
        __tablename__ = "entity"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]

    def _map(
        src_cls: type[Any],
        dest_cls: type[Any],
        src: Any,
        *,
        src_path: str | None = None,
        dest_path: str | None = None,
    ) -> _Entity:
        return _Entity(id=1, name="name")

    mock.mock(Repository[_Entity]).setup_callable(lambda r: r.add, lambda entity: entity)
    mock.mock(Mapper).setup(lambda m: m.map, _map)
    mock.injection.add_singleton(Service[_Entity])

    service = mock.injection.require(Service[_Entity])

    entity = service.create(None)

    assert entity.id == 1
    assert entity.name == "name"


def test_update() -> None:
    cache = Cache()

    mock = Mock(cache=cache)

    class _Entity(get_base("tests", cache=cache)):
        __tablename__ = "entity"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]

    def _map(
        src_cls: type[Any],
        dest_cls: type[Any],
        src: Any,
        dest: _Entity,
        *,
        src_path: str | None = None,
        dest_path: str | None = None,
    ) -> _Entity:
        return dest

    mock.mock(Repository[_Entity])
    mock.mock(Mapper).setup(lambda m: m.map, _map)
    mock.injection.add_singleton(Service[_Entity])

    service = mock.injection.require(Service[_Entity])

    entity = _Entity(id=1, name="name")

    entity2 = service.update(entity, None)

    assert entity2 is entity
    assert entity2.id == 1
    assert entity2.name == "name"


def test_fail_validate_non_nullable_column() -> None:
    cache = Cache()

    mock = Mock(cache=cache)

    class _Entity(get_base("tests", cache=cache)):
        __tablename__ = "entity"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]

    def _map(
        src_cls: type[Any],
        dest_cls: type[Any],
        src: Any,
        *,
        src_path: str | None = None,
        dest_path: str | None = None,
    ) -> _Entity:
        return _Entity(id=1, name=None)

    mock.mock(Repository[_Entity]).setup_callable(lambda r: r.add, lambda entity: entity)
    mock.mock(Mapper).setup(lambda m: m.map, _map)
    mock.injection.add_singleton(Service[_Entity])

    service = mock.injection.require(Service[_Entity])

    with pytest.raises(ColumnNotNullableError) as info:
        service.create(None)

    assert f"Column 'name' of entity {_Entity} must not contain a null value" == info.value.message


def test_fail_validate_wrong_column_type() -> None:
    cache = Cache()

    mock = Mock(cache=cache)

    class _Entity(get_base("tests", cache=cache)):
        __tablename__ = "entity"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str | None]
        value: Mapped[int]

    def _map(
        src_cls: type[Any],
        dest_cls: type[Any],
        src: Any,
        *,
        src_path: str | None = None,
        dest_path: str | None = None,
    ) -> _Entity:
        return _Entity(id=1, name=None, value="42")

    mock.mock(Repository[_Entity]).setup_callable(lambda r: r.add, lambda entity: entity)
    mock.mock(Mapper).setup(lambda m: m.map, _map)
    mock.injection.add_singleton(Service[_Entity])

    service = mock.injection.require(Service[_Entity])

    with pytest.raises(WrongColumnTypeError) as info:
        service.create(None)

    assert f"Column 'value' of entity {_Entity} must be of type {int}, got value '42'" == info.value.message
