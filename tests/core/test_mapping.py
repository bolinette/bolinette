import pytest
from typing import TypeVar, Generic

from bolinette import Cache
from bolinette.testing import Mock
from bolinette.utils import AttributeUtils
from bolinette.mapping import Mapper, Profile, mapping


def test_register_sequence() -> None:
    class _ParentSource:
        id: int

    class _Source(_ParentSource):
        name: str

    class _ParentDestination1:
        id: int

    class _ParentDestination2:
        attr: str

    class _Destination(_ParentDestination1, _ParentDestination2):
        value: str

    cache = Cache()

    @mapping(cache=cache)
    class DestinationProfile(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            e = self.register(_Source, _Destination).for_attr(
                lambda d: d.value,
                lambda opt: opt.map_from(lambda s: s.name),
            )

    mock = Mock(cache=cache)
    mock.injection.add(AttributeUtils, "singleton")
    mock.injection.add(Mapper, "singleton")

    mapper = mock.injection.require(Mapper)

    src = _Source()
    src.id = 0
    src.name = "test"

    dest = mapper.map(_Source, _Destination, src)

    assert dest.id == src.id
    assert dest.attr is None
    assert dest.value == src.name
