import os
from collections.abc import Callable
from typing import Any, Optional

import pytest

from bolinette import Cache, Environment, Logger, environment, CoreSection
from bolinette.exceptions import EnvironmentError
from bolinette.mapping import Mapper
from bolinette.testing import Mock
from bolinette.utils import FileUtils, PathUtils


def _setup_test(cache: Cache | None = None) -> Mock:
    mock = Mock(cache=cache)
    mock.mock(Logger[Any], match_all=True)
    mock.mock(PathUtils).setup(lambda p: p.env_path, lambda *values: "".join(values))
    mock.mock(FileUtils).setup(lambda f: f.read_yaml, lambda *_: {})
    mock.mock(Mapper).setup(lambda m: m.map, lambda *_a, **_k: None)
    mock.injection.add(Environment, "singleton", args=["test"])
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
    mock.injection.require(TestSection)

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
    mock.mock(FileUtils).setup(lambda f: f.read_yaml, lambda *_: {"test": {"a": False}})
    mock.injection.require(Environment)
    mock.injection.require(TestSection)


def test_env_file_not_found() -> None:
    cache = Cache()

    @environment("test", cache=cache)
    class TestSection:
        a: bool = True
        b: bool = True

    mock = _setup_test(cache)

    def _read_yaml(path) -> dict:
        match path:
            case "env.yaml":
                return {"test": {"a": False, "b": True}}
            case "env.test.yaml":
                raise FileNotFoundError()
            case "env.local.test.yaml":
                raise FileNotFoundError()
            case _:
                raise FileNotFoundError()

    mock.mock(FileUtils).setup(lambda f: f.read_yaml, _read_yaml)
    mock.injection.require(Environment)
    mock.injection.require(TestSection)


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
    mock.mock(FileUtils).setup(lambda f: f.read_yaml, _read_yaml)
    mock.injection.require(Environment)
    mock.injection.require(TestSection)


def test_os_env_conflict() -> None:
    os.environ["BLNT_TEST__A__A"] = "1"
    os.environ["BLNT_TEST__A"] = "2"

    mock = _setup_test()
    with pytest.raises(EnvironmentError) as info:
        mock.injection.require(Environment)

    assert f"OS variable 'BLNT_TEST__A' conflicts with other variables" in info.value.message

    del os.environ["BLNT_TEST__A__A"]
    del os.environ["BLNT_TEST__A"]


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

    assert (f"No 'test' section was found in the environment files") in info.value.message


def test_init_core_section() -> None:
    cache = Cache()

    environment("core", cache=cache)(CoreSection)

    mock = _setup_test(cache)

    def _read_yaml(path) -> dict:
        match path:
            case "env.yaml":
                return {"core": {"debug": True}}
            case _:
                raise FileNotFoundError()

    assert cache.debug is False

    mock.mock(FileUtils).setup(lambda f: f.read_yaml, _read_yaml)
    mock.mock(Mapper).setup(lambda m: m.map, lambda _st, _dt, _s, d, *_a, **_k: setattr(d, "debug", True))
    mock.injection.require(Environment)
    section = mock.injection.require(CoreSection)

    assert section.debug is True
    assert cache.debug is True
