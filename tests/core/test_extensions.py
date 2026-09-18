"""Extension resolution, ordering and registration into the application."""

from collections.abc import Sequence

import pytest
from escondite import Cache
from soupape import ServiceCollection

from bolinette.core import CoreExtension
from bolinette.core.exceptions import InitError
from bolinette.core.extensions import Extension, LoadedExtensions, resolve_extensions, sort_extensions
from tests.core.conftest import AppFactory


class ExtA(Extension):
    name = "a"
    dependencies: Sequence[type[Extension]] = ()

    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass


class ExtB(Extension):
    name = "b"
    dependencies: Sequence[type[Extension]] = (ExtA,)

    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass


class ExtC(Extension):
    name = "c"
    dependencies: Sequence[type[Extension]] = (ExtB,)

    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass


class ExtWithOption(Extension):
    name = "with_option"
    dependencies: Sequence[type[Extension]] = ()

    def __init__(self, value: int = 0) -> None:
        self.value = value

    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass


class ExtWithoutDefault(Extension):
    name = "without_default"
    dependencies: Sequence[type[Extension]] = ()

    def __init__(self, value: int) -> None:
        self.value = value

    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass


class ExtNeedsNoDefault(Extension):
    name = "needs_no_default"
    dependencies: Sequence[type[Extension]] = (ExtWithoutDefault,)

    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass


class TestSortExtensions:
    def test_dependencies_come_first(self) -> None:
        """An extension is placed after every extension it depends on."""
        c, b, a = ExtC(), ExtB(), ExtA()

        assert sort_extensions([c, b, a]) == [a, b, c]

    def test_first_types_are_placed_before_the_others(self) -> None:
        """Types given in `first` precede every extension that is not one of them."""
        a, opt = ExtA(), ExtWithOption()

        assert sort_extensions([a, opt], first=[ExtWithOption]) == [opt, a]

    def test_missing_dependency_is_ignored(self) -> None:
        """Sorting only orders the given instances and does not instantiate missing dependencies."""
        b = ExtB()

        assert sort_extensions([b]) == [b]

    def test_cycle_raises(self) -> None:
        """A dependency cycle is reported as an `InitError`."""

        class Left(Extension):
            name = "left"
            dependencies: Sequence[type[Extension]] = ()

            def register_services(self, services: ServiceCollection, cache: Cache) -> None:
                pass

        class Right(Extension):
            name = "right"
            dependencies: Sequence[type[Extension]] = (Left,)

            def register_services(self, services: ServiceCollection, cache: Cache) -> None:
                pass

        Left.dependencies = (Right,)

        with pytest.raises(InitError, match="circular dependency"):
            sort_extensions([Left(), Right()])


class TestResolveExtensions:
    def test_returns_given_extensions_sorted(self) -> None:
        """Extensions given out of order are returned in dependency order."""
        c, b, a = ExtC(), ExtB(), ExtA()

        assert resolve_extensions([c, b, a]) == [a, b, c]

    def test_instantiates_missing_dependencies(self) -> None:
        """A dependency that was not provided is instantiated with no arguments."""
        c = ExtC()

        loaded = resolve_extensions([c])

        assert [type(ext) for ext in loaded] == [ExtA, ExtB, ExtC]
        assert loaded[2] is c

    def test_keeps_provided_instance_of_dependency(self) -> None:
        """A dependency given explicitly keeps its options instead of being re-instantiated."""

        class Dependent(Extension):
            name = "dependent"
            dependencies: Sequence[type[Extension]] = (ExtWithOption,)

            def register_services(self, services: ServiceCollection, cache: Cache) -> None:
                pass

        opt = ExtWithOption(value=42)

        loaded = resolve_extensions([Dependent(), opt])

        assert loaded[0] is opt
        assert opt.value == 42

    def test_dependency_without_default_constructor_raises(self) -> None:
        """A missing dependency that cannot be built without arguments is reported."""
        with pytest.raises(InitError, match="add it explicitly"):
            resolve_extensions([ExtNeedsNoDefault()])

    def test_dependency_without_default_constructor_can_be_given(self) -> None:
        """Providing the dependency explicitly lifts the constructor restriction."""
        dep = ExtWithoutDefault(1)

        loaded = resolve_extensions([ExtNeedsNoDefault(), dep])

        assert loaded[0] is dep

    def test_same_type_twice_raises(self) -> None:
        """The same extension type cannot be provided twice."""
        with pytest.raises(InitError, match="provided twice"):
            resolve_extensions([ExtA(), ExtA()])

    def test_implicit_extensions_are_loaded_and_placed_first(self) -> None:
        """Implicit types are instantiated when missing and always come first."""
        loaded = resolve_extensions([ExtA()], implicit=[ExtWithOption])

        assert [type(ext) for ext in loaded] == [ExtWithOption, ExtA]

    def test_implicit_dependencies_are_also_first(self) -> None:
        """The dependencies of an implicit extension are part of the implicit closure."""
        loaded = resolve_extensions([ExtWithOption()], implicit=[ExtB])

        assert [type(ext) for ext in loaded] == [ExtA, ExtB, ExtWithOption]

    def test_no_extensions_yields_implicit_only(self) -> None:
        """Resolving nothing returns the implicit extensions."""
        loaded = resolve_extensions([], implicit=[ExtA])

        assert [type(ext) for ext in loaded] == [ExtA]


class TestLoadedExtensions:
    def test_iterates_in_order(self) -> None:
        """Iteration yields the extensions in the order they were given."""
        a, b = ExtA(), ExtB()

        assert list(LoadedExtensions([a, b])) == [a, b]
        assert len(LoadedExtensions([a, b])) == 2

    def test_get_by_type(self) -> None:
        """`get` returns the instance of the requested type."""
        a, b = ExtA(), ExtB()

        assert LoadedExtensions([a, b]).get(ExtB) is b

    def test_get_missing_raises(self) -> None:
        """`get` raises a `KeyError` naming the type when it was not loaded."""
        with pytest.raises(KeyError, match="ExtB"):
            LoadedExtensions([ExtA()]).get(ExtB)


class TestAppExtensions:
    async def test_core_is_always_loaded_first(self, make_app: AppFactory) -> None:
        """`CoreExtension` is loaded even when no extension is given and precedes the others."""
        blnt = await make_app([ExtA()])

        assert [type(ext) for ext in blnt.extensions] == [CoreExtension, ExtA]

    async def test_no_extensions(self, make_app: AppFactory) -> None:
        """An application built with no extension only has the core one."""
        blnt = await make_app()

        assert [type(ext) for ext in blnt.extensions] == [CoreExtension]

    async def test_dependencies_are_loaded(self, make_app: AppFactory) -> None:
        """Dependencies of the given extensions are loaded transitively."""
        blnt = await make_app([ExtC()])

        assert [type(ext) for ext in blnt.extensions] == [CoreExtension, ExtA, ExtB, ExtC]

    async def test_register_services_is_called_with_app_cache(self, make_app: AppFactory, cache: Cache) -> None:
        """Each extension registers its services with a cache that falls back on the user cache."""
        seen: list[Cache] = []

        class Recording(Extension):
            name = "recording"
            dependencies: Sequence[type[Extension]] = ()

            def register_services(self, services: ServiceCollection, cache: Cache) -> None:
                seen.append(cache)

        await make_app([Recording()])

        assert len(seen) == 1
        assert seen[0] is not cache

    async def test_extension_services_are_injectable(self, make_app: AppFactory) -> None:
        """Services registered by an extension are resolvable from the application."""

        class Service:
            pass

        class Registering(Extension):
            name = "registering"
            dependencies: Sequence[type[Extension]] = ()

            def register_services(self, services: ServiceCollection, cache: Cache) -> None:
                services.add_singleton(Service)

        services = ServiceCollection()
        await make_app([Registering()], services=services)

        assert services.is_registered(Service)

    async def test_extension_instance_is_a_singleton(self, make_app: AppFactory) -> None:
        """Every loaded extension can be injected under its own type."""
        opt = ExtWithOption(value=7)
        services = ServiceCollection()
        await make_app([opt], services=services)

        assert services.is_registered(ExtWithOption)
        assert services.is_registered(CoreExtension)

    async def test_loaded_extensions_is_injectable(self, make_app: AppFactory) -> None:
        """`LoadedExtensions` is registered as a singleton holding the loaded instances."""
        services = ServiceCollection()
        blnt = await make_app([ExtA()], services=services)

        assert services.is_registered(LoadedExtensions)
        assert isinstance(blnt.extensions.get(ExtA), ExtA)
