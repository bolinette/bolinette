import os
from collections.abc import Callable
from typing import Any, Optional, Union

import pytest

from bolinette.core import Cache, Environment, InjectionStrategy, Logger, environment
from bolinette.core.exceptions import EnvironmentError, InitError
from bolinette.core.testing import Mock
from bolinette.core.utils import FileUtils, PathUtils


def _setup_test(cache: Cache | None = None) -> Mock:
    mock = Mock(cache=cache)
    mock.mock(Logger)
    mock.mock(PathUtils).setup("env_path", lambda *values: "".join(values))
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {})
    mock.injection.add(Environment, InjectionStrategy.Singleton, args=["test"])
    return mock


def test_init_env_from_os() -> None:
    cache = Cache()

    class SubSection:
        a: str
        b: str

    @environment("test", cache=cache)
    class TestSection:
        a: SubSection
        b: SubSection
        c: str
        d: int = 6

    os.environ["BLNT_TEST__A__A"] = "1"
    os.environ["BLNT_TEST__A__B"] = "2"
    os.environ["BLNT_TEST__B__A"] = "3"
    os.environ["BLNT_TEST__B__B"] = "4"
    os.environ["BLNT_TEST__C"] = "5"

    mock = _setup_test(cache)
    mock.injection.require(Environment)
    test = mock.injection.require(TestSection)

    assert test.a.a == "1"
    assert test.a.b == "2"
    assert test.b.a == "3"
    assert test.b.b == "4"
    assert test.c == "5"
    assert test.d == 6

    del os.environ["BLNT_TEST__A__A"]
    del os.environ["BLNT_TEST__A__B"]
    del os.environ["BLNT_TEST__B__A"]
    del os.environ["BLNT_TEST__B__B"]
    del os.environ["BLNT_TEST__C"]


def test_parse_yaml_file() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: bool = True
        b: bool = True

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": False}})
    mock.injection.require(Environment)
    test = mock.injection.require(TestSection)

    assert test.a is False
    assert test.b is True


def test_fail_missing_attribute() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: bool = True
        b: bool = True
        c: bool

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": False}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"Section {TestSection}: "
        "no value to bind found in environment and no default value set"
    ) in info.value.message


def test_file_override() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: int
        b: int
        c: int

    def _read_yaml(path) -> dict:
        match path:
            case "env.yaml":
                return {"test": {"a": 1, "b": 1, "c": 1}}
            case "env.test.yaml":
                return {"test": {"a": 2, "b": 2}}
            case "env.local.test.yaml":
                return {"test": {"a": 3}}
            case _:
                return {}

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", _read_yaml)
    mock.injection.require(Environment)
    test = mock.injection.require(TestSection)

    assert test.a == 3
    assert test.b == 2
    assert test.c == 1


def test_non_empty_init() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        def __init__(self, _) -> None:
            pass

    mock = _setup_test(cache)
    with pytest.raises(InitError) as info:
        mock.injection.require(Environment)

    assert (
        f"Section {TestSection} must have an empty __init__ method"  # type: ignore
        in info.value.message
    )


def test_non_empty_sub_init() -> None:
    cache = Cache()

    class SubTestSection:
        def __init__(self, _) -> None:
            pass

    @environment("test", cache=cache)
    class TestSection:
        sub: SubTestSection

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"sub": {}}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"Section {SubTestSection} must have an empty __init__ method"
        in info.value.message
    )


def test_no_dict_to_map() -> None:
    cache = Cache()

    class SubTestSection:
        pass

    @environment("test", cache=cache)
    class TestSection:
        sub: SubTestSection

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"sub": 4}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"Section {TestSection}.sub is typed has a class and can only be mapped from a dictionnary"
        in info.value.message
    )


def test_no_literal() -> None:
    cache = Cache()

    class SubTestSection:
        pass

    @environment("test", cache=cache)
    class TestSection:
        sub: "SubTestSection"

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"sub": 4}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"Section {TestSection}.sub: no literal allowed in type hints"
        in info.value.message
    )


def test_os_env_conflict() -> None:
    os.environ["BLNT_TEST__A__A"] = "1"
    os.environ["BLNT_TEST__A"] = "2"

    mock = _setup_test()
    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(Environment)

    assert (
        f"OS variable 'BLNT_TEST__A' conflicts with other variables"
        in info.value.message
    )

    del os.environ["BLNT_TEST__A__A"]
    del os.environ["BLNT_TEST__A"]


def test_decorate_func() -> None:
    def fail_func() -> None:
        pass

    with pytest.raises(InitError) as info:
        environment("fail")(fail_func)  # type: ignore

    assert (
        f"{fail_func} must be a class to be decorated with @{environment.__name__}"  # type: ignore
        in info.value.message
    )


def test_fail_cast_type() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: int

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": "1"}})
    mock.injection.require(Environment)
    test = mock.injection.require(TestSection)

    assert test.a == 1


def test_fail_wrong_type() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: int

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": "test"}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"Section {TestSection}.a: unable to bind value test to type {int}"
        in info.value.message
    )


def test_optional_value() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: int | None

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": None}})
    mock.injection.require(Environment)
    test = mock.injection.require(TestSection)

    assert test.a is None


def test_optional_value_bis() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: Optional[int]

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": None}})
    mock.injection.require(Environment)
    test = mock.injection.require(TestSection)

    assert test.a is None


def test_optional_with_value() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: int | None

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": 1}})
    mock.injection.require(Environment)
    test = mock.injection.require(TestSection)

    assert test.a == 1


def test_fail_not_optional() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: int

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": None}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"Section {TestSection}.a: attemting to bind None value to a non-nullable attribute"
        in info.value.message
    )


def test_hint_any() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: Any
        b: Any

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": 1, "b": [1, 2]}})
    mock.injection.require(Environment)
    test = mock.injection.require(TestSection)

    assert test.a == 1
    assert test.b == [1, 2]


def test_fail_no_union() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: int | bool

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": 1}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert f"Section {TestSection}.a: type unions are not allowed" in info.value.message


def test_fail_no_union_bis() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: Union[int, bool]

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": 1}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert f"Section {TestSection}.a: type unions are not allowed" in info.value.message


def test_fail_unknow_type() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: Callable[[], None]

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup("read_yaml", lambda *_: {"test": {"a": 1}})
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"Unable to bind value to section {TestSection}.a, "
        "be sure to type hint with only classes and buit-in types"
    ) in info.value.message


def test_fail_no_section() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: Callable[[], None]

    mock = _setup_test(cache)
    mock.mock(FileUtils)
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"No 'test' section was found in the environment files"
    ) in info.value.message


def test_builtin_list_attribute() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: list[int]
        b: list[str]
        c: list[float]
        d: list[bool]

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup(
        "read_yaml",
        lambda *_: {
            "test": {"a": [1, 2], "b": ["a", "b"], "c": [1.1, 2.2], "d": [True, False]}
        },
    )
    mock.injection.require(Environment)

    t = mock.injection.require(TestSection)

    assert t.a == [1, 2]
    assert t.b == ["a", "b"]
    assert t.c == [1.1, 2.2]
    assert t.d == [True, False]


def test_list_attribute_bad_cast() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: list[int]

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup(
        "read_yaml",
        lambda *_: {"test": {"a": ["1", "b"]}},
    )
    mock.injection.require(Environment)

    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(TestSection)

    assert (
        f"Section {TestSection}.a[1]: unable to bind value b to type {int}"
        in info.value.message
    )


def test_sub_object_in_list() -> None:
    cache = Cache()

    class SubTestSection:
        a: int
        b: str

    @environment("test", cache=cache)
    class TestSection:
        subs: list[SubTestSection]

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup(
        "read_yaml",
        lambda *_: {"test": {"subs": [{"a": 1, "b": "a"}, {"a": 2, "b": "b"}]}},
    )
    mock.injection.require(Environment)

    t = mock.injection.require(TestSection)

    assert len(t.subs) == 2
    assert t.subs[0].a == 1
    assert t.subs[0].b == "a"
    assert t.subs[1].a == 2
    assert t.subs[1].b == "b"


def test_non_generic_list() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: list

    mock = _setup_test(cache)
    mock.mock(FileUtils).setup(
        "read_yaml",
        lambda *_: {"test": {"a": [1, "b"]}},
    )
    mock.injection.require(Environment)

    t = mock.injection.require(TestSection)

    assert t.a == [1, "b"]
