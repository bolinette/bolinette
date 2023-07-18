import pytest

from bolinette.core import Cache, Extension
from bolinette.core.exceptions import InitError


def test_sort_extensions() -> None:
    cache = Cache()

    e1 = Extension(cache)
    e2 = Extension(cache, [e1])

    extensions = [e1, e2]
    sorted_extensions = Extension.sort_extensions(extensions)

    assert sorted_extensions == extensions


def test_sort_extensions_reversed() -> None:
    cache = Cache()

    e1 = Extension(cache)
    e2 = Extension(cache, [e1])

    extensions = [e2, e1]
    sorted_extensions = Extension.sort_extensions(extensions)

    assert sorted_extensions == [e1, e2]


def test_fail_circular_dependencies() -> None:
    cache = Cache()

    e1 = Extension(cache)
    e2 = Extension(cache, [e1])
    e1.dependencies = [e2]

    with pytest.raises(InitError) as info:
        Extension.sort_extensions([e2, e1])

    assert "A circular dependency was detected in the loaded extensions" == info.value.message


def test_merge_caches() -> None:
    c1 = Cache()
    c1.add("key1", 1)
    c1.add("key1", 2)
    c1.add("key2", 1)

    c2 = Cache()
    c2.add("key1", 2)
    c2.add("key1", 3)
    c2.add("key3", 1)

    e1 = Extension(c1)
    e2 = Extension(c2)

    cache = Extension.merge_caches([e1, e2])

    assert "key1" in cache
    assert "key2" in cache
    assert "key3" in cache
    assert cache.get("key1") == [1, 2, 2, 3]
    assert cache.get("key2") == [1]
    assert cache.get("key3") == [1]
