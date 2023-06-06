from typing import Any

import pytest

from bolinette import Cache
from bolinette.exceptions import MappingError
from bolinette.mapping import Mapper, Profile, mapping, type_mapper
from bolinette.mapping.mapper import DefaultTypeMapper, IntegerTypeMapper, StringTypeMapper
from bolinette.testing import Mock
from bolinette.types import Type


def load_default_mappers(mapper: Mapper) -> None:
    mapper.set_default_type_mapper(DefaultTypeMapper)
    mapper.add_type_mapper(Type(int), IntegerTypeMapper)
    mapper.add_type_mapper(Type(str), StringTypeMapper)


def test_init_type_mappers_from_cache() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")

    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination:
        value: int

    @type_mapper(_Destination, cache=cache)
    class _:
        def __init__(self, runner) -> None:
            self.runner = runner

        def map(
            self,
            path: str,
            src_t: Type[Any],
            dest_t: Type[_Destination],
            src: Any,
            dest: _Destination | None,
        ) -> _Destination:
            assert isinstance(src, _Source)
            if dest is None:
                dest = _Destination()
            dest.value = src.value + 1
            return dest

    mapper = mock.injection.require(Mapper)

    src = _Source(1)
    dest = mapper.map(_Source, _Destination, src)

    assert dest.value == 2


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
    load_default_mappers(mapper)

    s = _Source("test")

    d = mapper.map(_Source, _Destination, s)

    assert isinstance(s, _Source)
    assert isinstance(d, _Destination)
    assert d.value == s.value
    assert d is not s


def test_map_with_map_from() -> None:
    class _Source:
        def __init__(self, value: str) -> None:
            self.value = value

    class _Destination:
        content: str

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.value)
            )

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    s = _Source("test")

    d = mapper.map(_Source, _Destination, s)

    assert isinstance(s, _Source)
    assert isinstance(d, _Destination)
    assert d.content == s.value
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
    load_default_mappers(mapper)

    s = _Source("test")

    d = mapper.map(_Source, _Destination, s)

    assert isinstance(s, _Source)
    assert isinstance(d, _Destination)
    assert d.value == s.value
    assert d is not s


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
    load_default_mappers(mapper)

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
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    with pytest.raises(MappingError) as info:
        mapper.map(_Source, _Destination, _Source())

    assert (
        "Attribute '$.value', Not found in source, could not bind a None "
        "value to non nullable type test_fail_no_default_value.<locals>._Value" == info.value.message
    )


def test_map_explicit_ignore() -> None:
    class _Source:
        name: str

        def __init__(self, name: str) -> None:
            self.name = name

    class _Destination:
        name: str | None

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(lambda dest: dest.name, lambda opt: opt.ignore())

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    s = _Source("test")

    d = mapper.map(_Source, _Destination, s)

    assert s.name == "test"
    assert d.name == None


def test_fail_map_ignore_non_nullable() -> None:
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
    load_default_mappers(mapper)

    s = _Source("test")

    with pytest.raises(MappingError) as info:
        mapper.map(_Source, _Destination, s)

    assert "Attribute '$.name', Could not ignore attribute, type str is not nullable" == info.value.message


def test_fail_invalid_int_cast() -> None:
    class _Source:
        def __init__(self, value: str) -> None:
            self.value = value

    class _Destination:
        value: int

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source("test")

    with pytest.raises(MappingError) as info:
        mapper.map(_Source, _Destination, src)

    assert "Attribute '$.value', Could not convert value 'test' to int" == info.value.message


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
    load_default_mappers(mapper)

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
    load_default_mappers(mapper)

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

    with pytest.raises(MappingError) as info:
        mock.injection.require(Mapper)

    assert (
        "Mapping (test_fail_included_base_not_found.<locals>._Source -> "
        "test_fail_included_base_not_found.<locals>._Destination): "
        "Could not find base mapping (test_fail_included_base_not_found.<locals>._ParentSource -> "
        "test_fail_included_base_not_found.<locals>._ParentDestination). "
        "Make sure the mappings are declared in the right order."
    ) == info.value.message


def test_map_before_after() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination:
        value: int

    cache = Cache()

    order: list[str] = []

    def before_map(src: _Source, dest: _Destination) -> None:
        assert src.value == 1
        assert not hasattr(dest, "value")
        order.append("before")

    def after_map(src: _Source, dest: _Destination) -> None:
        assert src.value == dest.value
        order.append("after")

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination).before_mapping(before_map).after_mapping(after_map)

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(1)

    mapper.map(_Source, _Destination, src)

    assert order == ["before", "after"]


def test_nested_mapping() -> None:
    class _NestedSource:
        def __init__(self, value: str) -> None:
            self.value = value

    class _NestedDestination:
        content: str

    cache = Cache()

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_NestedSource, _NestedDestination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.value)
            )

    class _Source:
        def __init__(self, nested: _NestedSource) -> None:
            self.nested = nested

    class _Destination:
        content: _NestedDestination

    @mapping(cache=cache)
    class _(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.nested)
            )

    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(_NestedSource("test"))

    d = mapper.map(_Source, _Destination, src)

    assert src is not d
    assert src.nested is not d.content
    assert src.nested.value == d.content.content
    assert isinstance(d.content, _NestedDestination)


def test_mapping_list() -> None:
    class _Source:
        def __init__(self, values: list[int]) -> None:
            self.values = values

    class _Destination:
        values: list[int]

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source([1, 2, 3])
    dest = mapper.map(_Source, _Destination, src)

    assert dest.values == src.values
    assert dest.values is not src.values
