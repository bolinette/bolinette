import pytest

from bolinette.core import Cache
from bolinette.core.exceptions import InitError
from bolinette.core.extensions import Extension, ExtensionModule, sort_extensions


class _MockModule:
    def __init__(self, ext: type[Extension]) -> None:
        self.__blnt_ext__ = ext
        self.__name__ = ""


def test_sort_extensions() -> None:
    class _Ext1:
        def __init__(self, cache: Cache) -> None:
            self.name: str = "e1"
            self.dependencies: list[ExtensionModule[Extension]] = []

    class _Ext2:
        def __init__(self, cache: Cache) -> None:
            self.name: str = "e2"
            self.dependencies: list[ExtensionModule[Extension]] = [_MockModule(_Ext1)]

    cache = Cache()
    e1 = _Ext1(cache)
    e2 = _Ext2(cache)

    extensions: list[Extension] = [e1, e2]
    sorted_extensions = sort_extensions(extensions)

    assert sorted_extensions == [e1, e2]


def test_sort_extensions_reversed() -> None:
    class _Ext1:
        def __init__(self, cache: Cache) -> None:
            self.name: str = "e1"
            self.dependencies: list[ExtensionModule[Extension]] = []

    class _Ext2:
        def __init__(self, cache: Cache) -> None:
            self.name: str = "e2"
            self.dependencies: list[ExtensionModule[Extension]] = [_MockModule(_Ext1)]

    e1 = _Ext1(Cache())
    e2 = _Ext2(Cache())

    extensions: list[Extension] = [e2, e1]
    sorted_extensions = sort_extensions(extensions)

    assert sorted_extensions == [e1, e2]


def test_fail_circular_dependencies() -> None:
    class _Ext1:
        def __init__(self, cache: Cache) -> None:
            self.name: str = "e1"
            self.dependencies: list[ExtensionModule[Extension]] = [_MockModule(_Ext2)]

    class _Ext2:
        def __init__(self, cache: Cache) -> None:
            self.name: str = "e2"
            self.dependencies: list[ExtensionModule[Extension]] = [_MockModule(_Ext1)]

    e1 = _Ext1(Cache())
    e2 = _Ext2(Cache())

    with pytest.raises(InitError) as info:
        sort_extensions([e2, e1])

    assert "A circular dependency was detected in the loaded extensions" == info.value.message
