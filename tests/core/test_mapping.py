import pytest

from bolinette import Cache
from bolinette.mapping import Mapper, Profile, mapping
from bolinette.testing import Mock


def test_map_simple_attr() -> None:
    class _Source:
        value: str

        def __init__(self, value: str) -> None:
            self.value = value

    class _Destination:
        value: str

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)

    s = _Source("test")

    d = mapper.map(_Source, _Destination, s)

    assert isinstance(s, _Source)
    assert isinstance(d, _Destination)
    assert d.value == s.value
    assert d is not s


def test_map_implicit_ignore() -> None:
    class _Source:
        name: str

        def __init__(self, name: str) -> None:
            self.name = name

    class _Destination:
        value: str

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)

    s = _Source("test")

    d = mapper.map(_Source, _Destination, s)

    assert s.name == "test"
    assert d.value == ""


def test_map_explicit_ignore() -> None:
    class _Source:
        name: str

        def __init__(self, name: str) -> None:
            self.name = name

    class _Destination:
        name: str

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(lambda dest: dest.name, lambda opt: opt.ignore())

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)

    s = _Source("test")

    d = mapper.map(_Source, _Destination, s)

    assert s.name == "test"
    assert d.name == ""


def test_map_with_bases() -> None:
    class _ParentSource:
        id: int

    class _Source(_ParentSource):
        name: str

    class _ParentDestination1:
        id: int

    class _ParentDestination2:
        attr: str

    class _Destination(_ParentDestination1, _ParentDestination2):
        name: str

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)

    src = _Source()
    src.id = 0
    src.name = "test"

    dest = mapper.map(_Source, _Destination, src)

    assert dest.id == src.id
    assert dest.attr == ""
    assert dest.name == src.name


def test_map_with_custom_dest() -> None:
    class _Source:
        name: str

        def __init__(self, name) -> None:
            self.name = name

    class _Destination:
        name: str

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)

    src = _Source("test")
    dest = _Destination()

    mapped = mapper.map(_Source, _Destination, src, dest)

    assert mapped is dest
    assert mapped.name == dest.name == src.name


def test_map_include_base() -> None:
    class _ParentSource:
        def __init__(self, name: str) -> None:
            self.name = name

    class _ParentDestination:
        id: str

    class _Source(_ParentSource):
        def __init__(self, name: str, value: int) -> None:
            super().__init__(name)
            self.value = value

    class _Destination(_ParentDestination):
        content: int

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_ParentSource, _ParentDestination).for_attr(
                lambda dest: dest.id, lambda opt: opt.map_from(lambda src: src.name)
            )

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination).include(_ParentSource, _ParentDestination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.value)
            )

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)

    src = _Source("test", 42)

    dest = mapper.map(_Source, _Destination, src)

    assert dest is not src
    assert dest.id == src.name
    assert dest.content == src.value
