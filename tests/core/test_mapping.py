import pytest

from bolinette import Cache
from bolinette.exceptions import InitMappingError, MappingError
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


def test_map_source_no_hint() -> None:
    class _Source:
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


def test_map_default_value_none() -> None:
    class _Source:
        pass

    class _Destination:
        value: str | None

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)

    d = mapper.map(_Source, _Destination, _Source())

    assert d.value is None


def test_fail_no_default_value() -> None:
    class _Source:
        pass

    class _Value:
        def __init__(self, value) -> None:
            self.value = value

    class _Destination:
        value: _Value

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    with pytest.raises(MappingError) as info:
        mock.injection.require(Mapper)

    assert (
        f"Type {_Destination}, Attribute 'value', Default value for attribute could not be determined"
        == info.value.message
    )


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


def test_fail_included_base_not_found() -> None:
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
            self.register(_Source, _Destination).include(_ParentSource, _ParentDestination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.value)
            )

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")

    with pytest.raises(InitMappingError) as info:
        mock.injection.require(Mapper)

    assert (
        f"Mapping {_Source} -> {_Destination}: "
        f"Could not find base mapping {_ParentSource} -> {_ParentDestination}. "
        f"Make sure the mappings are declared in the right order."
    ) == info.value.message


def test_map_before_after() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination:
        value: int

    cache = Cache()

    def before_map(src: _Source, dest: _Destination) -> None:
        assert src.value == 1
        assert not hasattr(dest, "value")

    def after_map(src: _Source, dest: _Destination) -> None:
        assert src.value == dest.value

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination).before_mapping(before_map).after_mapping(after_map)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)

    src = _Source(1)

    mapper.map(_Source, _Destination, src)
