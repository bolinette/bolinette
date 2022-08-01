import os

from bolinette.core import Cache, Environment, Injection, InjectionStrategy, environment, Logger
from bolinette.core.inject import InjectionContext
from bolinette.core.utils import PathUtils, FileUtils


def _setup_inject(cache: Cache | None = None) -> Injection:
    inject = Injection(cache or Cache(), InjectionContext())
    inject.add(Logger, InjectionStrategy.Singleton)
    inject.add(Environment, InjectionStrategy.Singleton, args=["test"])
    inject.add(
        PathUtils, InjectionStrategy.Singleton, args=[PathUtils.dirname(__file__)]
    )
    inject.add(FileUtils, InjectionStrategy.Singleton)
    return inject


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

    inject = _setup_inject(cache)
    inject.require(Environment)
    test = inject.require(TestSection)

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


def test_parse_yaml_file():
    pass
