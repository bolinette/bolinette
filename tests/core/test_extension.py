import pytest

from bolinette.core import Extension
from bolinette.core.exceptions import InitError


class _MockModule:
    def __init__(self, ext: Extension) -> None:
        self.__blnt_ext__ = ext


def test_sort_extensions() -> None:
    e1 = Extension("e1")
    e2 = Extension("e2", [_MockModule(e1)])

    extensions = [e1, e2]
    sorted_extensions = Extension.sort_extensions(extensions)

    assert sorted_extensions == extensions


def test_sort_extensions_reversed() -> None:
    e1 = Extension("e1")
    e2 = Extension("e2", [_MockModule(e1)])

    extensions = [e2, e1]
    sorted_extensions = Extension.sort_extensions(extensions)

    assert sorted_extensions == [e1, e2]


def test_fail_circular_dependencies() -> None:
    e1 = Extension("e1")
    e2 = Extension("e2", [_MockModule(e1)])
    e1.dependencies = [e2]

    with pytest.raises(InitError) as info:
        Extension.sort_extensions([e2, e1])

    assert "A circular dependency was detected in the loaded extensions" == info.value.message
