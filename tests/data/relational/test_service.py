from sqlalchemy.orm import Mapped, mapped_column

from bolinette import Cache
from bolinette.ext.data.relational import Repository, Service, get_base
from bolinette.mapping import Mapper
from bolinette.testing import Mock


def test_create() -> None:
    cache = Cache()

    mock = Mock(cache=cache)

    class _Entity(get_base("tests", cache=cache)):
        __tablename__ = "entity"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]

    mock.mock(Repository[_Entity]).setup("add", lambda e: e)
    mock.mock(Mapper).setup("map", lambda cs, cd, s: _Entity(id=1, name="name"))
    mock.injection.add(Service[_Entity], "singleton")

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

    mock.mock(Repository[_Entity])
    mock.mock(Mapper).setup("map", lambda cs, cd, s, d: d)
    mock.injection.add(Service[_Entity], "singleton")

    service = mock.injection.require(Service[_Entity])

    entity = _Entity(id=1, name="name")

    entity2 = service.update(entity, None)

    assert entity2 is entity
    assert entity2.id == 1
    assert entity2.name == "name"
