import pytest

from bolinette.testing import Mock


class _TestInjectedClass:
    def __init__(self, v1: str, v2: str, v3: str) -> None:
        self.v1 = v1
        self._v2 = v2
        self._v3 = v3

    @property
    def v2(self) -> str:
        return self._v2

    def get_v3(self) -> str:
        return self._v3

    @staticmethod
    def get_v4(value: str) -> str:
        return value


class _TestClass:
    def __init__(self, injected: _TestInjectedClass) -> None:
        self.i = injected


def test_mock_get_mocked_attr() -> None:
    mock = Mock()
    mock.mock(_TestInjectedClass).setup("v1", "1")
    mock.injection.add(_TestClass, "singleton")

    t = mock.injection.require(_TestClass)
    assert t.i.v1 == "1"


def test_mock_get_mocked_attr_property() -> None:
    mock = Mock()
    mock.mock(_TestInjectedClass).setup("v2", "2")
    mock.injection.add(_TestClass, "singleton")

    t = mock.injection.require(_TestClass)
    assert t.i.v2 == "2"


def test_mock_get_mocked_attr_callable() -> None:
    mock = Mock()
    mock.mock(_TestInjectedClass).setup("get_v3", lambda: "3")
    mock.injection.add(_TestClass, "singleton")

    t = mock.injection.require(_TestClass)
    assert t.i.get_v3() == "3"


def test_mock_get_mocked_attr_callable_args() -> None:
    mock = Mock()
    mock.mock(_TestInjectedClass).setup("get_v4", lambda value: value)
    mock.injection.add(_TestClass, "singleton")

    t = mock.injection.require(_TestClass)
    assert t.i.get_v4("4") == "4"


def test_mock_two_mock_calls() -> None:
    mock = Mock()
    mock.mock(_TestInjectedClass).setup("v1", "1")
    mock.mock(_TestInjectedClass).setup("get_v3", lambda: "3")
    mock.injection.add(_TestClass, "singleton")

    t = mock.injection.require(_TestClass)
    assert t.i.v1 == "1"
    assert t.i.get_v3() == "3"


def test_mock_fail_not_mocked() -> None:
    mock = Mock()
    mock.mock(_TestInjectedClass)
    mock.injection.add(_TestClass, "singleton")

    t = mock.injection.require(_TestClass)
    with pytest.raises(KeyError) as info:
        t.i.get_v3()

    assert f"'get_v3' attribute has not been mocked in {_TestInjectedClass}" in str(
        info.value
    )


def test_mock_dummy_mode() -> None:
    mock = Mock()
    mock.mock(_TestInjectedClass).dummy()
    mock.injection.add(_TestClass, "singleton")

    t = mock.injection.require(_TestClass)

    assert t.i.v1 is None
    assert t.i.v2 is None
    assert t.i.get_v3() is None
    assert t.i.get_v4("test") is None
