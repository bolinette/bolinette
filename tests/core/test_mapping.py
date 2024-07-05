# pyright: reportUninitializedInstanceVariable=false
from typing import Any, NotRequired, TypedDict

import pytest

from bolinette.core import Cache
from bolinette.core.expressions import ExpressionNode
from bolinette.core.expressions.exceptions import MaxDepthExpressionError
from bolinette.core.mapping import Mapper, MappingRunner, Profile, mapping, type_mapper
from bolinette.core.mapping.exceptions import MappingError
from bolinette.core.mapping.mapper import (
    BoolTypeMapper,
    DefaultTypeMapper,
    FloatTypeMapper,
    IntegerTypeMapper,
    StringTypeMapper,
)
from bolinette.core.testing import Mock
from bolinette.core.types import Type


def load_default_mappers(mapper: Mapper) -> None:
    mapper.set_default_type_mapper(DefaultTypeMapper)
    mapper.add_type_mapper(Type(int), IntegerTypeMapper)
    mapper.add_type_mapper(Type(str), StringTypeMapper)
    mapper.add_type_mapper(Type(float), FloatTypeMapper)
    mapper.add_type_mapper(Type(bool), BoolTypeMapper)


def test_init_type_mappers_from_cache() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination:
        value: int

    class TestTypeMapper:
        def __init__(self, runner: MappingRunner) -> None:
            self.runner = runner

        def map(
            self,
            src_expr: ExpressionNode,
            src_t: Type[Any],
            dest_expr: ExpressionNode,
            dest_t: Type[_Destination],
            src: Any,
            dest: _Destination | None,
            exc_grp: list[MappingError] | None,
        ) -> _Destination:
            assert isinstance(src, _Source)
            if dest is None:
                dest = _Destination()
            dest.value = src.value + 1
            return dest

    cache = Cache()
    type_mapper(_Destination, cache=cache)(TestTypeMapper)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
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

    mock = Mock()
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

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.value)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
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

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination)

    cache = Cache()
    mapping(cache=cache)(TestProfile)
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
        def __init__(self, value: Any) -> None:
            self.value = value

    class _Destination:
        value: _Value

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    with pytest.raises(MappingError) as info:
        mapper.map(_Source, _Destination, _Source())

    assert (
        "Destination path 'test_fail_no_default_value.<locals>._Destination.value', "
        "From source path 'test_fail_no_default_value.<locals>._Source.value', "
        "Source path not found, could not bind a None "
        "value to non nullable type test_fail_no_default_value.<locals>._Value" == info.value.message
    )


def test_map_default_value() -> None:
    class _Source:
        pass

    class _Destination:
        value: int = 1

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    dest = mapper.map(_Source, _Destination, _Source())

    assert dest.value == 1


def test_map_explicit_ignore() -> None:
    class _Source:
        name: str

        def __init__(self, name: str) -> None:
            self.name = name

    class _Destination:
        name: str | None

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(lambda dest: dest.name, lambda opt: opt.ignore())

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    s = _Source("test")

    d = mapper.map(_Source, _Destination, s)

    assert s.name == "test"
    assert d.name is None


def test_fail_map_ignore_non_nullable() -> None:
    class _Source:
        name: str

        def __init__(self, name: str) -> None:
            self.name = name

    class _Destination:
        name: str

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(lambda dest: dest.name, lambda opt: opt.ignore())

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    s = _Source("test")

    with pytest.raises(MappingError) as info:
        mapper.map(_Source, _Destination, s)

    assert (
        "Destination path 'test_fail_map_ignore_non_nullable.<locals>._Destination.name', "
        "Could not ignore attribute, type str is not nullable" == info.value.message
    )


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

    assert (
        "Destination path 'test_fail_invalid_int_cast.<locals>._Destination.value', "
        "From source path 'test_fail_invalid_int_cast.<locals>._Source.value', "
        "Could not convert value 'test' to int" == info.value.message
    )


def test_fail_invalid_float_cast() -> None:
    class _Source:
        def __init__(self, value: str) -> None:
            self.value = value

    class _Destination:
        value: float

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source("test")

    with pytest.raises(MappingError) as info:
        mapper.map(_Source, _Destination, src)

    assert (
        "Destination path 'test_fail_invalid_float_cast.<locals>._Destination.value', "
        "From source path 'test_fail_invalid_float_cast.<locals>._Source.value', "
        "Could not convert value 'test' to float" == info.value.message
    )


def test_cast_to_bool() -> None:
    class _Source:
        def __init__(self, value1: str, value2: int) -> None:
            self.value1 = value1
            self.value2 = value2

    class _Destination:
        value1: bool
        value2: bool

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source("test", 0)
    dest = mapper.map(_Source, _Destination, src)

    assert dest.value1 is True
    assert dest.value2 is False


def test_map_with_custom_dest() -> None:
    class _Source:
        name: str

        def __init__(self, name: str) -> None:
            self.name = name

    class _Destination:
        name: str

    class TestProfile(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination)

    cache = Cache()
    mapping(cache=cache)(TestProfile)
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

    class TestProfile1(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_ParentSource, _ParentDestination).for_attr(
                lambda dest: dest.id, lambda opt: opt.map_from(lambda src: src.name)
            )

    class TestProfile2(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination).include(_ParentSource, _ParentDestination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.value)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile1)
    mapping(cache=cache)(TestProfile2)
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

    class TestProfile(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination).include(_ParentSource, _ParentDestination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.value)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
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

    order: list[str] = []

    def before_map(src: _Source, dest: _Destination) -> None:
        assert src.value == 1
        assert not hasattr(dest, "value")
        order.append("before")

    def after_map(src: _Source, dest: _Destination) -> None:
        assert src.value == dest.value
        order.append("after")

    class TestProfile(Profile):
        def __init__(self) -> None:
            Profile.__init__(self)
            self.register(_Source, _Destination).before_mapping(before_map).after_mapping(after_map)

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(1)

    mapper.map(_Source, _Destination, src)

    assert order == ["before", "after"]


def test_nested_mapping_no_profile() -> None:
    class _NestedSource:
        def __init__(self, value: str) -> None:
            self.value = value

    class _NestedDestination:
        value: str

    class _Source:
        def __init__(self, nested: _NestedSource) -> None:
            self.content = nested

    class _Destination:
        content: _NestedDestination

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(_NestedSource("test"))

    d = mapper.map(_Source, _Destination, src)

    assert src is not d
    assert src.content is not d.content
    assert src.content.value == d.content.value
    assert isinstance(d.content, _NestedDestination)


def test_nested_mapping_with_profile() -> None:
    class _NestedSource:
        def __init__(self, value: str) -> None:
            self.value = value

    class _NestedDestination:
        content: str

    class _Source:
        def __init__(self, nested: _NestedSource) -> None:
            self.nested = nested

    class _Destination:
        content: _NestedDestination

    class TestProfile1(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_NestedSource, _NestedDestination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.value)
            )

    class TestProfile2(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest.content, lambda opt: opt.map_from(lambda src: src.nested)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile1)
    mapping(cache=cache)(TestProfile2)
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


def test_mapping_iterables() -> None:
    class _Source:
        def __init__(self, values: list[int]) -> None:
            self.values = values

    class _Destination:
        v1: list[int]
        v2: set[int]
        v3: tuple[int]

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            (
                self.register(_Source, _Destination)
                .for_attr(lambda dest: dest.v1, lambda opt: opt.map_from(lambda src: src.values))
                .for_attr(lambda dest: dest.v2, lambda opt: opt.map_from(lambda src: src.values))
                .for_attr(lambda dest: dest.v3, lambda opt: opt.map_from(lambda src: src.values))
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source([1, 2, 3])
    dest = mapper.map(_Source, _Destination, src)

    assert isinstance(dest.v1, list)
    assert dest.v1 == [1, 2, 3]
    assert isinstance(dest.v2, set)
    assert dest.v2 == {1, 2, 3}
    assert isinstance(dest.v3, tuple)
    assert dest.v3 == (1, 2, 3)


def test_map_to_str_dict() -> None:
    class _Source:
        def __init__(self, values: tuple[int, str, float]) -> None:
            self.a = values[0]
            self.b = values[1]
            self.c = values[2]

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source((1, "2", 3.3))
    dest = mapper.map(_Source, dict[str, str], src)

    assert len(dest) == 3
    assert dest["a"] == "1"
    assert dest["b"] == "2"
    assert dest["c"] == "3.3"


def test_map_to_dict_mixed() -> None:
    class _Source:
        def __init__(self, values: tuple[int, str, float]) -> None:
            self.a = values[0]
            self.b = values[1]
            self.c = values[2]

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source((1, "2", 3.3))
    dest = mapper.map(_Source, dict[str, Any], src)

    assert len(dest) == 3
    assert dest["a"] == 1
    assert dest["b"] == "2"
    assert dest["c"] == 3.3


def test_map_to_any() -> None:
    class _Nested1:
        pass

    class _Source1:
        def __init__(self, n: _Nested1) -> None:
            self.n = n

    class _Nested2:
        pass

    class _Source2:
        def __init__(self, n: _Nested2) -> None:
            self.n = n

    class _Destination:
        n: Any

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    s1 = _Source1(_Nested1())
    d1 = mapper.map(_Source1, _Destination, s1)
    assert isinstance(d1.n, _Nested1)
    assert d1.n is not s1.n

    s2 = _Source2(_Nested2())
    d2 = mapper.map(_Source2, _Destination, s2)
    assert isinstance(d2.n, _Nested2)
    assert d2.n is not s2.n


def test_map_to_union_type() -> None:
    class _NestedSource:
        pass

    class _Source:
        def __init__(self, n: _NestedSource) -> None:
            self.n = n

    class _NestedDest1:
        pass

    class _NestedDest2:
        pass

    class _Destination:
        n: _NestedDest1 | _NestedDest2

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest.n, lambda opt: opt.map_from(lambda src: src.n).use_type(_NestedDest2)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    s = _Source(_NestedSource())
    d = mapper.map(_Source, _Destination, s)

    assert isinstance(d.n, _NestedDest2)


def test_fail_map_to_union_type() -> None:
    class _NestedSource:
        pass

    class _Source:
        def __init__(self, n: _NestedSource) -> None:
            self.n = n

    class _NestedDest1:
        pass

    class _NestedDest2:
        pass

    class _Destination:
        n: _NestedDest1 | _NestedDest2

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    s = _Source(_NestedSource())
    with pytest.raises(MappingError) as info:
        mapper.map(_Source, _Destination, s)

    assert (
        "Destination path 'test_fail_map_to_union_type.<locals>._Destination.n', "
        f"Destination type {Type(_NestedDest1 | _NestedDest2)} is a union,"
        " please use use_type(...) in profile" == info.value.message
    )


def test_fail_map_use_type_not_in_union() -> None:
    class _NestedSource:
        pass

    class _Source:
        def __init__(self, n: _NestedSource) -> None:
            self.n = n

    class _NestedDest1:
        pass

    class _NestedDest2:
        pass

    class _NestedDest3:
        pass

    class _Destination:
        n: _NestedDest1 | _NestedDest2

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest.n, lambda opt: opt.map_from(lambda src: src.n).use_type(_NestedDest3)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    s = _Source(_NestedSource())
    with pytest.raises(MappingError) as info:
        mapper.map(_Source, _Destination, s)

    assert (
        "Destination path 'test_fail_map_use_type_not_in_union.<locals>._Destination.n', "
        "From source path 'test_fail_map_use_type_not_in_union.<locals>._Source.n', "
        "Selected type test_fail_map_use_type_not_in_union.<locals>._NestedDest3 is not assignable to "
        f"{Type(_NestedDest1 | _NestedDest2)}" == info.value.message
    )


def test_map_collection() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination:
        value: int

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    sources = [_Source(1), _Source(2), _Source(3)]
    destinations = mapper.map(list[_Source], list[_Destination], sources)

    assert len(destinations) == 3
    assert destinations is not sources
    assert all(isinstance(d, _Destination) for d in destinations)
    assert destinations[0].value == 1
    assert destinations[1].value == 2
    assert destinations[2].value == 3


def test_fail_map_collection_from_not_iter() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination:
        value: int

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    source = _Source(1)
    with pytest.raises(MappingError) as info:
        mapper.map(_Source, list[_Destination], source)

    assert (
        "Destination path 'list[test_fail_map_collection_from_not_iter.<locals>._Destination]', "
        "From source path 'test_fail_map_collection_from_not_iter.<locals>._Source', "
        "Could not map non iterable type test_fail_map_collection_from_not_iter.<locals>._Source "
        "to list[test_fail_map_collection_from_not_iter.<locals>._Destination]" == info.value.message
    )


def test_map_existing_collection() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    sources = [1, 2, 3]
    dest_l: list[int] = []
    dest_s: set[int] = set()
    dest_t: tuple[int, ...] = ()
    n_dest_l = mapper.map(list[int], list[int], sources, dest_l)
    n_dest_s = mapper.map(list[int], set[int], sources, dest_s)

    assert dest_l is n_dest_l
    assert dest_l == n_dest_l == [1, 2, 3]
    assert dest_s is n_dest_s
    assert dest_s == n_dest_s == {1, 2, 3}

    with pytest.raises(MappingError) as info:
        mapper.map(list[int], tuple[int, ...], sources, dest_t)

    assert (
        "Destination path 'tuple[int, ...]', "
        "Could not use an existing tuple instance, tuples are immutable" == info.value.message
    )


def test_map_from_dict() -> None:
    class _Destination:
        id: int
        name: str

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    dest = mapper.map(dict[str, Any], _Destination, {"id": 1, "name": "test"})

    assert dest.id == 1
    assert dest.name == "test"


def test_fail_map_from_dict() -> None:
    class _Destination:
        id: int
        name: str

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    with pytest.raises(MappingError) as info:
        mapper.map(dict[str, Any], _Destination, {"id": 1})

    assert (
        "Destination path 'test_fail_map_from_dict.<locals>._Destination.name', "
        "From source path 'dict[str, Any]['name']', "
        "Source path not found, could not bind a None value to non nullable type str" == info.value.message
    )


def test_map_from_dict_nested() -> None:
    class _SubDestination:
        value: float
        active: bool

    class _Destination:
        id: int
        name: str
        subs: list[_SubDestination]

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    dest = mapper.map(
        dict[str, Any],
        _Destination,
        {"id": 1, "name": "test", "subs": [{"value": 1.1, "active": True}, {"value": 2.2, "active": False}]},
    )

    assert dest.id == 1
    assert dest.name == "test"
    assert len(dest.subs) == 2
    assert all(isinstance(s, _SubDestination) for s in dest.subs)
    assert dest.subs[0].value == 1.1
    assert dest.subs[0].active is True
    assert dest.subs[1].value == 2.2
    assert dest.subs[1].active is False


def test_map_dict_to_dict() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    dest = mapper.map(dict[str, Any], dict[str, int], {"at1": 1, "at2": "2"})

    assert dest["at1"] == 1
    assert dest["at2"] == 2


def test_map_attr_from_child() -> None:
    class _NestedSource:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Source:
        def __init__(self, nested: _NestedSource) -> None:
            self.nested = nested

    class _Destination:
        value: int

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest.value, lambda opt: opt.map_from(lambda src: src.nested.value)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(_NestedSource(1))

    d = mapper.map(_Source, _Destination, src)

    assert src is not d
    assert src.nested.value == d.value


def test_fail_map_from_nested() -> None:
    class _NestedSource:
        def __init__(self, value: int) -> None:
            self.value = value

    class _NestedDestination:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Source:
        def __init__(self, nested: _NestedSource) -> None:
            self.nested = nested

    class _Destination:
        nested: _NestedDestination

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest.nested.value, lambda opt: opt.map_from(lambda src: src.nested.value)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")

    with pytest.raises(MaxDepthExpressionError) as info:
        mock.injection.require(Mapper)

    assert (
        info.value.message == "Expression test_fail_map_from_nested.<locals>._Destination.nested.value, "
        "Expression exceeds allowed depth"
    )


def test_map_typed_dict() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination(TypedDict):
        content: int

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest["content"], lambda opt: opt.map_from(lambda src: src.value)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(4)
    dest = mapper.map(_Source, _Destination, src)

    assert dest["content"] == 4


def test_map_typed_dict_from_nested() -> None:
    class _NestedSource:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Source:
        def __init__(self, nested: _NestedSource) -> None:
            self.nested = nested

    class _Destination(TypedDict):
        content: int

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest["content"], lambda opt: opt.map_from(lambda src: src.nested.value)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(_NestedSource(4))
    dest = mapper.map(_Source, _Destination, src)

    assert dest["content"] == 4


def test_fail_map_from_nested_typed_dict() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _NestedDestination:
        value: int

    class _Destination(TypedDict):
        nested: _NestedDestination

    class TestProfile(Profile):
        def __init__(self) -> None:
            super().__init__()
            self.register(_Source, _Destination).for_attr(
                lambda dest: dest["nested"].value, lambda opt: opt.map_from(lambda src: src.value)
            )

    cache = Cache()
    mapping(cache=cache)(TestProfile)
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")

    with pytest.raises(MaxDepthExpressionError) as info:
        mock.injection.require(Mapper)

    assert (
        info.value.message == "Expression test_fail_map_from_nested_typed_dict.<locals>._Destination['nested'].value, "
        "Expression exceeds allowed depth"
    )


def test_map_typed_dict_not_required_attr() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination(TypedDict):
        value: int
        content: NotRequired[int]

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(4)
    dest = mapper.map(_Source, _Destination, src)

    assert dest["value"] == 4
    assert "content" not in dest


def test_map_typed_dict_non_total_dict() -> None:
    class _Source:
        def __init__(self, value: int) -> None:
            self.value = value

    class _Destination(TypedDict, total=False):
        value: int
        content: int

    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Mapper, "singleton")
    mapper = mock.injection.require(Mapper)
    load_default_mappers(mapper)

    src = _Source(4)
    dest = mapper.map(_Source, _Destination, src)

    assert "value" in dest and dest["value"] == 4
    assert "content" not in dest
