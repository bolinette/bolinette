"""The `command` decorator, argument parsing and command execution through the application."""

import inspect
from argparse import ArgumentParser, Namespace
from typing import Annotated, Any, Literal, override

import pytest
from escondite import Cache
from peritype import FWrap, TWrap, wrap_func, wrap_type
from soupape import ServiceCollection
from soupape.extension import InjectionScope, ResolutionContext, ResolutionFunction, ServiceResolver

from bolinette.core import meta, startup
from bolinette.core.commands import CommandArg, CommandOption, command
from bolinette.core.commands._bundled._debug import build_type_tree, format_type_tree
from bolinette.core.commands._meta import CommandMeta
from bolinette.core.commands._parser import BytesArgparserAction
from bolinette.core.commands.exceptions import CommandHelpError, CommandUsageError
from bolinette.core.exceptions import InitError
from tests.core.conftest import AppFactory


def _commands(cache: Cache) -> list[FWrap[..., Any]]:
    return list(cache.get(CommandMeta.KEY, raises=False))


class TestCommandDecorator:
    def test_decorator_form(self, cache: Cache) -> None:
        """`command(name, summary)` used as a decorator registers the function and its metadata."""

        @command("hello", "Says hello", cache=cache)
        async def hello() -> None:
            pass

        assert [f.func for f in _commands(cache)] == [hello]
        assert meta.get(hello, CommandMeta.KEY) == CommandMeta("hello", "Says hello", True)

    def test_direct_form(self, cache: Cache) -> None:
        """`command(func, name, summary)` registers an existing function and returns it."""

        async def hello() -> None:
            pass

        assert command(hello, "hello", "Says hello", cache=cache, run_startup=False) is hello
        assert meta.get(hello, CommandMeta.KEY) == CommandMeta("hello", "Says hello", False)

    def test_invalid_arguments_raise(self, cache: Cache) -> None:
        """Any other argument shape is a programming error."""
        with pytest.raises(TypeError):
            command("hello", cache=cache)  # pyright: ignore[reportCallIssue]


class TestCommandParams:
    def test_arg_defaults(self) -> None:
        """`CommandArg()` describes a positional argument without default or summary."""
        arg = CommandArg()

        assert arg.default is None
        assert arg.summary is None

    def test_option_with_shorthand(self) -> None:
        """`CommandOption("x")` describes an option with a one-letter shorthand."""
        opt = CommandOption("x", summary="An option", default=1)

        assert opt.shorthand == "x"
        assert opt.summary == "An option"
        assert opt.default == 1

    def test_option_without_shorthand(self) -> None:
        """An option needs no shorthand."""
        assert CommandOption().shorthand is None


class TestRunCommand:
    async def test_runs_command_and_returns_code(self, make_app: AppFactory, cache: Cache) -> None:
        """`run_command` runs the matching command and returns its exit code."""
        calls: list[str] = []

        @command("hello", "Says hello", cache=cache)
        async def hello() -> int:
            calls.append("hello")
            return 3

        blnt = await make_app()

        assert await blnt.run_command(["hello"]) == 3
        assert calls == ["hello"]

    async def test_command_without_return_yields_none(self, make_app: AppFactory, cache: Cache) -> None:
        """A command that returns nothing yields `None` as its exit code."""

        @command("hello", "Says hello", cache=cache)
        async def hello() -> None:
            pass

        blnt = await make_app()

        assert await blnt.run_command(["hello"]) is None

    async def test_nested_command_path(self, make_app: AppFactory, cache: Cache) -> None:
        """Command names with spaces build a tree of sub-commands."""
        calls: list[str] = []

        @command("db migrate", "Runs migrations", cache=cache)
        async def migrate() -> None:
            calls.append("migrate")

        @command("db seed", "Seeds the database", cache=cache)
        async def seed() -> None:
            calls.append("seed")

        blnt = await make_app()
        await blnt.run_command(["db", "seed"])
        await blnt.run_command(["db", "migrate"])

        assert calls == ["seed", "migrate"]

    async def test_services_are_injected(self, make_app: AppFactory, cache: Cache) -> None:
        """Command parameters without `CommandArg` or `CommandOption` annotation are resolved by the injector."""
        seen: list[Cache] = []

        @command("hello", "Says hello", cache=cache)
        async def hello(cache: Cache) -> None:
            seen.append(cache)

        blnt = await make_app()
        await blnt.run_command(["hello"])

        assert len(seen) == 1

    async def test_run_startup_by_default(self, make_app: AppFactory, cache: Cache) -> None:
        """Commands trigger the application startup before running unless told otherwise."""
        calls: list[str] = []

        @startup(cache=cache)
        async def init() -> None:
            calls.append("startup")

        @command("hello", "Says hello", cache=cache)
        async def hello() -> None:
            calls.append("hello")

        blnt = await make_app()
        await blnt.run_command(["hello"])

        assert calls == ["startup", "hello"]
        assert blnt.started

    async def test_skip_startup(self, make_app: AppFactory, cache: Cache) -> None:
        """A command with `run_startup=False` does not start the application."""
        calls: list[str] = []

        @startup(cache=cache)
        async def init() -> None:
            calls.append("startup")

        @command("hello", "Says hello", cache=cache, run_startup=False)
        async def hello() -> None:
            calls.append("hello")

        blnt = await make_app()
        await blnt.run_command(["hello"])

        assert calls == ["hello"]
        assert not blnt.started

    async def test_no_command_raises_help(
        self, make_app: AppFactory, cache: Cache, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Running without a command raises the root help with exit code 1, printing nothing itself."""
        blnt = await make_app()

        with pytest.raises(CommandHelpError) as info:
            await blnt.run_command([])

        assert info.value.code == 1
        assert "Bolinette Framework" in info.value.message
        assert capsys.readouterr() == ("", "")

    async def test_incomplete_path_raises_group_help(self, make_app: AppFactory, cache: Cache) -> None:
        """Stopping at a command group raises that group's help with exit code 1."""

        @command("db migrate", "Runs migrations", cache=cache)
        async def migrate() -> None:
            pass

        blnt = await make_app()

        with pytest.raises(CommandHelpError) as info:
            await blnt.run_command(["db"])

        assert info.value.code == 1
        assert "migrate" in info.value.message

    async def test_unknown_command_raises_usage_error(self, make_app: AppFactory) -> None:
        """An unknown command is a usage error carrying the usage text and exit code 2."""
        blnt = await make_app()

        with pytest.raises(CommandUsageError) as info:
            await blnt.run_command(["nope"])

        assert info.value.code == 2
        assert info.value.message.startswith("usage:")
        assert "invalid choice: 'nope'" in info.value.message

    async def test_conflicting_paths_raise(self, make_app: AppFactory, cache: Cache) -> None:
        """Two commands registered under the same path fail at application build."""

        @command("hello", "First", cache=cache)
        async def first() -> None:
            pass

        @command("hello", "Second", cache=cache)
        async def second() -> None:
            pass

        with pytest.raises(InitError, match="Conflict"):
            await make_app()

    async def test_bundled_debug_command(self, make_app: AppFactory, capsys: pytest.CaptureFixture[str]) -> None:
        """The bundled `debug injection` command lists the registered types."""
        blnt = await make_app()

        assert await blnt.run_command(["debug", "injection", "-f", "Bolinette"]) is None
        out = capsys.readouterr().out
        assert "All registered types" in out
        assert "Bolinette: singleton" in out


class TestCommandArguments:
    async def test_positional_string(self, make_app: AppFactory, cache: Cache) -> None:
        """A positional `str` argument is taken from the command line."""
        received: list[str] = []

        @command("greet", "Greets", cache=cache)
        async def greet(name: Annotated[str, CommandArg()]) -> None:
            received.append(name)

        blnt = await make_app()
        await blnt.run_command(["greet", "Bob"])

        assert received == ["Bob"]

    async def test_bare_class_annotation_is_rejected(self, make_app: AppFactory, cache: Cache) -> None:
        """Annotating with `CommandArg` or `CommandOption` itself instead of an instance fails at build."""

        @command("greet", "Greets", cache=cache)
        async def greet(name: Annotated[str, CommandArg], loud: Annotated[bool, CommandOption] = False) -> None:
            pass

        with pytest.raises(InitError, match="CommandArg\\(\\) instead of the bare class"):
            await make_app()

    async def test_int_and_float_are_converted(self, make_app: AppFactory, cache: Cache) -> None:
        """Numeric arguments are converted from their string form."""
        received: list[tuple[int, float]] = []

        @command("calc", "Computes", cache=cache)
        async def calc(count: Annotated[int, CommandArg()], ratio: Annotated[float, CommandArg()]) -> None:
            received.append((count, ratio))

        blnt = await make_app()
        await blnt.run_command(["calc", "3", "0.5"])

        assert received == [(3, 0.5)]

    async def test_invalid_int_is_rejected(self, make_app: AppFactory, cache: Cache) -> None:
        """A value that cannot be converted is a usage error."""

        @command("calc", "Computes", cache=cache)
        async def calc(count: Annotated[int, CommandArg()]) -> None:
            pass

        blnt = await make_app()

        with pytest.raises(CommandUsageError, match="invalid int value"):
            await blnt.run_command(["calc", "three"])

    async def test_bytes_argument(self, make_app: AppFactory, cache: Cache) -> None:
        """A `bytes` argument is encoded from the command line string."""
        received: list[bytes] = []

        @command("raw", "Raw", cache=cache)
        async def raw(data: Annotated[bytes, CommandArg()]) -> None:
            received.append(data)

        blnt = await make_app()
        await blnt.run_command(["raw", "abc"])

        assert received == [b"abc"]

    async def test_option_with_long_and_short_flags(self, make_app: AppFactory, cache: Cache) -> None:
        """An option is accepted under its long name and its shorthand."""
        received: list[str] = []

        @command("greet", "Greets", cache=cache)
        async def greet(name: Annotated[str, CommandOption("n")]) -> None:
            received.append(name)

        blnt = await make_app()
        await blnt.run_command(["greet", "--name", "Bob"])
        await blnt.run_command(["greet", "-n", "Ann"])

        assert received == ["Bob", "Ann"]

    async def test_required_option_is_enforced(self, make_app: AppFactory, cache: Cache) -> None:
        """A non-nullable option without default must be given."""

        @command("greet", "Greets", cache=cache)
        async def greet(name: Annotated[str, CommandOption()]) -> None:
            pass

        blnt = await make_app()

        with pytest.raises(CommandUsageError, match="required: --name"):
            await blnt.run_command(["greet"])

    async def test_option_with_default(self, make_app: AppFactory, cache: Cache) -> None:
        """The parameter default is used when the option is omitted."""
        received: list[str] = []

        @command("greet", "Greets", cache=cache)
        async def greet(name: Annotated[str, CommandOption()] = "World") -> None:
            received.append(name)

        blnt = await make_app()
        await blnt.run_command(["greet"])

        assert received == ["World"]

    async def test_nullable_option_is_optional(self, make_app: AppFactory, cache: Cache) -> None:
        """A nullable option without default is `None` when omitted."""
        received: list[str | None] = []

        @command("greet", "Greets", cache=cache)
        async def greet(name: Annotated[str | None, CommandOption()]) -> None:
            received.append(name)

        blnt = await make_app()
        await blnt.run_command(["greet"])

        assert received == [None]

    async def test_nullable_positional_is_rejected(self, make_app: AppFactory, cache: Cache) -> None:
        """A positional argument cannot be nullable."""

        @command("greet", "Greets", cache=cache)
        async def greet(name: Annotated[str | None, CommandArg()]) -> None:
            pass

        with pytest.raises(InitError, match="cannot be nullable"):
            await make_app()

    async def test_bool_flag_defaults_to_false(self, make_app: AppFactory, cache: Cache) -> None:
        """A `bool` option defaulting to `False` is a flag that stores `True` when present."""
        received: list[bool] = []

        @command("run", "Runs", cache=cache)
        async def run(verbose: Annotated[bool, CommandOption("v")] = False) -> None:
            received.append(verbose)

        blnt = await make_app()
        await blnt.run_command(["run"])
        await blnt.run_command(["run", "-v"])

        assert received == [False, True]

    async def test_bool_flag_defaults_to_true(self, make_app: AppFactory, cache: Cache) -> None:
        """A `bool` option defaulting to `True` is a flag that stores `False` when present."""
        received: list[bool] = []

        @command("run", "Runs", cache=cache)
        async def run(color: Annotated[bool, CommandOption()] = True) -> None:
            received.append(color)

        blnt = await make_app()
        await blnt.run_command(["run"])
        await blnt.run_command(["run", "--color"])

        assert received == [True, False]

    async def test_bool_flag_without_default(self, make_app: AppFactory, cache: Cache) -> None:
        """A `bool` option without default is a plain flag."""
        received: list[bool] = []

        @command("run", "Runs", cache=cache)
        async def run(verbose: Annotated[bool, CommandOption()]) -> None:
            received.append(verbose)

        blnt = await make_app()
        await blnt.run_command(["run"])
        await blnt.run_command(["run", "--verbose"])

        assert received == [False, True]

    async def test_literal_choices(self, make_app: AppFactory, cache: Cache) -> None:
        """A `Literal` of strings restricts the accepted values."""
        received: list[str] = []

        @command("log", "Logs", cache=cache)
        async def log(level: Annotated[Literal["info", "debug"], CommandArg()]) -> None:
            received.append(level)

        blnt = await make_app()
        await blnt.run_command(["log", "debug"])

        assert received == ["debug"]
        with pytest.raises(CommandUsageError, match="invalid choice"):
            await blnt.run_command(["log", "trace"])

    async def test_literal_int_choices(self, make_app: AppFactory, cache: Cache) -> None:
        """A `Literal` of integers converts and restricts the accepted values."""
        received: list[int] = []

        @command("log", "Logs", cache=cache)
        async def log(level: Annotated[Literal[1, 2], CommandArg()]) -> None:
            received.append(level)

        blnt = await make_app()
        await blnt.run_command(["log", "2"])

        assert received == [2]

    async def test_single_literal_is_a_constant_flag(self, make_app: AppFactory, cache: Cache) -> None:
        """A single-value `Literal` option stores that value when present."""
        received: list[str | None] = []

        @command("run", "Runs", cache=cache)
        async def run(mode: Annotated[Literal["fast"] | None, CommandOption()]) -> None:
            received.append(mode)

        blnt = await make_app()
        await blnt.run_command(["run"])
        await blnt.run_command(["run", "--mode"])

        assert received == [None, "fast"]

    async def test_mixed_literal_is_rejected(self, make_app: AppFactory, cache: Cache) -> None:
        """A `Literal` mixing value types is not a valid argument type."""

        @command("run", "Runs", cache=cache)
        async def run(mode: Annotated[Literal["fast", 1], CommandArg()]) -> None:
            pass

        with pytest.raises(InitError, match="not a valid argument type"):
            await make_app()

    async def test_list_option_appends(self, make_app: AppFactory, cache: Cache) -> None:
        """A `list` option collects every occurrence."""
        received: list[list[str] | None] = []

        @command("run", "Runs", cache=cache)
        async def run(tags: Annotated[list[str] | None, CommandOption("t")]) -> None:
            received.append(tags)

        blnt = await make_app()
        await blnt.run_command(["run", "-t", "a", "-t", "b"])
        await blnt.run_command(["run"])

        assert received == [["a", "b"], None]

    async def test_list_of_ints(self, make_app: AppFactory, cache: Cache) -> None:
        """Items of a `list[int]` option are converted."""
        received: list[list[int]] = []

        @command("run", "Runs", cache=cache)
        async def run(ids: Annotated[list[int], CommandOption()]) -> None:
            received.append(ids)

        blnt = await make_app()
        await blnt.run_command(["run", "--ids", "1", "--ids", "2"])

        assert received == [[1, 2]]

    async def test_unsupported_type_is_rejected(self, make_app: AppFactory, cache: Cache) -> None:
        """A parameter type the parser cannot handle fails at application build."""

        @command("run", "Runs", cache=cache)
        async def run(data: Annotated[dict[str, str], CommandArg()]) -> None:
            pass

        with pytest.raises(InitError, match="not allowed as a command argument"):
            await make_app()

    async def test_summary_appears_in_help(
        self, make_app: AppFactory, cache: Cache, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The argument summary is printed in the command help."""

        @command("greet", "Greets someone", cache=cache)
        async def greet(name: Annotated[str, CommandArg(summary="Who to greet")]) -> None:
            pass

        blnt = await make_app()

        with pytest.raises(CommandHelpError) as info:
            await blnt.run_command(["greet", "--help"])

        assert info.value.code == 0
        assert "Who to greet" in info.value.message
        assert capsys.readouterr() == ("", "")


class TestLiteralFlags:
    async def test_literal_true_option(self, make_app: AppFactory, cache: Cache) -> None:
        """A `Literal[True]` option is a flag that stores `True` when present and `False` otherwise."""
        received: list[bool | None] = []

        @command("run", "Runs", cache=cache)
        async def run(force: Annotated[Literal[True] | None, CommandOption()]) -> None:
            received.append(force)

        blnt = await make_app()
        await blnt.run_command(["run"])
        await blnt.run_command(["run", "--force"])

        assert received == [False, True]

    async def test_literal_false_option(self, make_app: AppFactory, cache: Cache) -> None:
        """A `Literal[False]` option is a flag that stores `False` when present."""
        received: list[bool | None] = []

        @command("run", "Runs", cache=cache)
        async def run(color: Annotated[Literal[False] | None, CommandOption()]) -> None:
            received.append(color)

        blnt = await make_app()
        await blnt.run_command(["run", "--color"])

        assert received == [False]


class TestBytesAction:
    def test_rejects_non_string_values(self) -> None:
        """The bytes action only knows how to encode a single string value."""
        parser = ArgumentParser()
        action: BytesArgparserAction[bytes] = BytesArgparserAction(["--data"], "data")

        with pytest.raises(TypeError):
            action(parser, Namespace(), ["a", "b"])


class Base:
    pass


class Impl(Base):
    pass


class FixedResolver(ServiceResolver[..., Any]):
    """A resolver that is not tied to a registered implementation."""

    @property
    @override
    def name(self) -> str:
        return "fixed"

    @property
    @override
    def scope(self) -> InjectionScope:
        return InjectionScope.SINGLETON

    @property
    @override
    def required(self) -> TWrap[Any]:
        return wrap_type(Base)

    @override
    def get_resolution_hints(self, context: ResolutionContext) -> dict[str, TWrap[Any]]:
        return {}

    @override
    def get_instance_function(self) -> FWrap[..., Any]:
        return wrap_func(self.get_resolution_func)

    @override
    def get_resolution_signature(self) -> inspect.Signature:
        return inspect.signature(self.get_resolution_func)

    @override
    def get_resolution_func(self, context: ResolutionContext) -> ResolutionFunction[..., Any]:
        return lambda: Base()


class TestDebugTree:
    def test_lines_show_scope_and_implementation(self) -> None:
        """Each registered type prints its scope, and its implementation when it differs."""
        services = ServiceCollection()
        services.add_singleton(Base, Impl)
        services.add_scoped(Impl)

        lines = [line.strip() for line in format_type_tree(build_type_tree(services))]

        assert lines[-2:] == [f"{Base.__qualname__} -> {Impl.__qualname__}: singleton", f"{Impl.__qualname__}: scoped"]

    def test_custom_resolver_shows_its_name(self) -> None:
        """A type served by a custom resolver prints the resolver name instead of an implementation."""
        services = ServiceCollection()
        services.add_resolver(FixedResolver())

        lines = format_type_tree(build_type_tree(services))

        assert lines[-1].endswith(": singleton (fixed)")

    def test_filter_keeps_matching_names_only(self) -> None:
        """The filter keeps types whose full name contains the given text."""
        services = ServiceCollection()
        services.add_singleton(Base)
        services.add_singleton(Impl)

        assert build_type_tree(services, "Nope") == {}
        assert len(format_type_tree(build_type_tree(services, "Impl"))) > 0

    @staticmethod
    def _fake(module: str, qualname: str) -> type[Any]:
        cls = type(qualname, (), {})
        cls.__module__ = module
        cls.__qualname__ = qualname
        return cls

    def test_types_are_sorted_by_name(self) -> None:
        """Types are placed in name order, so the output does not depend on registration order."""
        services = ServiceCollection()
        services.add_singleton(self._fake("pkg", "Zed"))
        services.add_singleton(self._fake("pkg", "Alpha"))

        lines = [line.strip() for line in format_type_tree(build_type_tree(services))]

        assert lines == ["pkg", "Alpha: singleton", "Zed: singleton"]

    def test_type_conflicting_with_module_raises(self) -> None:
        """A type placed where a module segment already is cannot be added to the tree."""
        services = ServiceCollection()
        services.add_singleton(self._fake("pkg.sub", "Child"))
        services.add_singleton(self._fake("pkg", "sub"))

        with pytest.raises(TypeError, match="conflicts with a module path"):
            build_type_tree(services)

    def test_module_conflicting_with_type_raises(self) -> None:
        """A module segment placed where a type already is cannot be added to the tree."""
        services = ServiceCollection()
        services.add_singleton(self._fake("pkg", "aaa"))
        services.add_singleton(self._fake("pkg.aaa", "zzz"))

        with pytest.raises(TypeError, match="conflicts with a registered type"):
            build_type_tree(services)
