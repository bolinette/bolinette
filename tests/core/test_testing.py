"""Testing helpers shipped with the core package: `Mock` and the temporary working directory tools."""

import os
from pathlib import Path

import pytest
from soupape import AsyncInjector, ServiceCollection

from bolinette.core.testing import Mock, tmp_cwd, with_tmp_cwd, with_tmp_cwd_async


class Repository:
    def __init__(self, url: str) -> None:
        self.url = url

    def fetch(self, key: str) -> str:
        raise NotImplementedError()

    def count(self) -> int:
        raise NotImplementedError()


class Service:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository


class Generic[T]:
    def get(self) -> T:
        raise NotImplementedError()


class TestMock:
    def test_mock_registers_a_singleton(self) -> None:
        """Mocking a type registers a singleton resolving to the mocked instance."""
        services = ServiceCollection()
        mock = Mock(services)

        wrapper = mock.mock(Repository)

        assert mock.services is services
        assert services.is_registered(Repository)
        assert repr(wrapper.instance) == "<Mocked[Repository]>"

    def test_instance_is_of_the_mocked_type(self) -> None:
        """The mocked instance passes `isinstance` checks against the original type."""
        wrapper = Mock(ServiceCollection()).mock(Repository)

        assert isinstance(wrapper.instance, Repository)

    def test_setup_attribute(self) -> None:
        """`setup` defines an attribute value read through an expression."""
        wrapper = Mock(ServiceCollection()).mock(Repository).setup(lambda r: r.url, "sqlite://")

        assert wrapper.instance.url == "sqlite://"

    def test_setup_callable(self) -> None:
        """`setup_callable` defines a method implementation."""
        wrapper = Mock(ServiceCollection()).mock(Repository)
        wrapper.setup_callable(lambda r: r.fetch, lambda key: f"value-{key}")

        assert wrapper.instance.fetch("a") == "value-a"

    def test_unmocked_attribute_raises(self) -> None:
        """Reading an attribute that was not set up is an error."""
        wrapper = Mock(ServiceCollection()).mock(Repository)

        with pytest.raises(KeyError, match="'url' attribute has not been mocked"):
            _ = wrapper.instance.url

    def test_dummy_returns_no_op_methods(self) -> None:
        """In dummy mode, unmocked methods of the original type become no-ops."""
        wrapper = Mock(ServiceCollection()).mock(Repository).dummy()

        assert wrapper.instance.fetch("a") is None
        assert wrapper.instance.count() is None

    def test_dummy_does_not_cover_plain_attributes(self) -> None:
        """Dummy mode only fakes callables, plain attributes still need a setup."""
        wrapper = Mock(ServiceCollection()).mock(Repository).dummy()

        assert wrapper.instance.url is None

    def test_setup_wins_over_dummy(self) -> None:
        """An explicit setup is used even in dummy mode."""
        wrapper = Mock(ServiceCollection()).mock(Repository).dummy()
        wrapper.setup_callable(lambda r: r.count, lambda: 3)

        assert wrapper.instance.count() == 3

    def test_dummy_can_be_disabled(self) -> None:
        """`dummy(False)` restores the strict behaviour."""
        wrapper = Mock(ServiceCollection()).mock(Repository).dummy().dummy(False)

        with pytest.raises(KeyError):
            wrapper.instance.count()

    def test_mocking_twice_returns_same_wrapper(self) -> None:
        """Mocking the same type again returns the existing wrapper."""
        mock = Mock(ServiceCollection())

        assert mock.mock(Repository) is mock.mock(Repository)

    def test_generic_type_is_mocked_by_origin(self) -> None:
        """A parametrized type is mocked through its origin and registered under the given alias."""
        services = ServiceCollection()
        mock = Mock(services)

        wrapper = mock.mock(Generic[int]).setup_callable(lambda g: g.get, lambda: 1)

        assert services.is_registered(Generic[int])
        assert wrapper.instance.get() == 1

    async def test_mock_is_injected(self) -> None:
        """A mocked dependency is injected into the services that need it."""
        services = ServiceCollection()
        services.add_singleton(Service)
        Mock(services).mock(Repository).setup(lambda r: r.url, "memory://")

        async with AsyncInjector(services) as injector:
            service = await injector.require(Service)

        assert service.repository.url == "memory://"


class TestTmpCwd:
    def test_context_manager_changes_and_restores_cwd(self) -> None:
        """`tmp_cwd` runs its body in a fresh directory and restores the previous one."""
        original = os.getcwd()

        with tmp_cwd() as tmp_dir:
            assert Path(os.getcwd()).resolve() == Path(tmp_dir).resolve()
            assert os.getcwd() != original

        assert os.getcwd() == original

    def test_directory_is_removed(self) -> None:
        """The temporary directory does not survive the context."""
        with tmp_cwd() as tmp_dir:
            pass

        assert not Path(tmp_dir).exists()

    def test_sync_decorator(self) -> None:
        """`with_tmp_cwd` wraps a function in `tmp_cwd` and forwards its result."""
        original = os.getcwd()

        @with_tmp_cwd
        def func(value: int) -> tuple[str, int]:
            return os.getcwd(), value

        cwd, value = func(3)

        assert cwd != original
        assert value == 3
        assert os.getcwd() == original

    async def test_async_decorator(self) -> None:
        """`with_tmp_cwd_async` does the same for coroutine functions."""
        original = os.getcwd()

        @with_tmp_cwd_async
        async def func() -> str:
            return os.getcwd()

        assert await func() != original
        assert os.getcwd() == original
