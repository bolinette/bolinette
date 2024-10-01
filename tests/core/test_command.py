import sys
from typing import Annotated, Any, Literal

import pytest
from pytest import CaptureFixture

from bolinette.core import Cache, command
from bolinette.core.command import Argument, Parser
from bolinette.core.command.command import CommandMeta
from bolinette.core.exceptions import InitError
from bolinette.core.logging import Logger
from bolinette.core.testing import Mock
from bolinette.core.types import Function


def test_decorate_command() -> None:
    cache = Cache()

    @command("command", "This is a test command", cache=cache)
    async def _command() -> None:
        pass

    assert CommandMeta in cache
    assert cache.get(CommandMeta, hint=Function)[0].func == _command


async def test_launch_command() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    value = 1

    exited = False

    def _catch_exit(*_) -> None:
        nonlocal exited
        exited = True

    @command("command", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value += 1

    parser = mock.injection.require(Parser)

    _exit = sys.exit
    sys.exit = _catch_exit

    cmd, args = parser.parse_command(["command"])
    await mock.injection.call(cmd.func.func, named_args=args)
    assert value == 2

    assert not exited

    sys.exit = _exit


async def test_launch_command_not_found() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)

    value = 1

    exited = False

    def _catch_exit(*_) -> None:
        nonlocal exited
        exited = True

    error_str = ""

    def _write_error(s: str) -> None:
        nonlocal error_str
        error_str = s

    mock.mock(Logger[Parser]).setup(lambda logger: logger.error, _write_error)

    @command("command", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value += 1

    parser = mock.injection.require(Parser)

    _exit = sys.exit
    sys.exit = _catch_exit

    parser.parse_command(["none"])
    assert value == 1

    assert exited

    sys.exit = _exit


async def test_launch_sub_command() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    value = 1

    exited = False

    def _catch_exit(*_) -> None:
        nonlocal exited
        exited = True

    @command("command inc", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value += 1

    @command("command dec", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value -= 1

    parser = mock.injection.require(Parser)

    _exit = sys.exit
    sys.exit = _catch_exit

    cmd, args = parser.parse_command(["command", "inc"])
    await mock.injection.call(cmd.func, named_args=args)
    assert value == 2

    cmd, args = parser.parse_command(["command", "dec"])
    await mock.injection.call(cmd.func, named_args=args)
    assert value == 1

    assert not exited

    sys.exit = _exit


async def test_launch_sub_command_not_found() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)

    value = 1

    exited = False

    def _catch_exit(*_) -> None:
        nonlocal exited
        exited = True

    @command("command inc", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value += 1

    @command("command dec", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value -= 1

    parser = mock.injection.require(Parser)

    _exit = sys.exit
    sys.exit = _catch_exit

    parser.parse_command(["command", "none"])
    assert value == 1

    assert exited

    sys.exit = _exit


async def test_command_argument() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    value = 0

    @command("command", "This is a test command", cache=cache)
    async def _(param: Annotated[int, Argument()]) -> None:
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    cmd, args = parser.parse_command(["command", "42"])
    await mock.injection.call(cmd.func, named_args=args)

    assert value == 42


async def test_command_with_injection() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    value = 0

    @command("command", "This is a test command", cache=cache)
    async def _(cache: Cache, param: Annotated[int, Argument]) -> None:
        nonlocal value
        value = len(cache.get(CommandMeta, hint=CommandMeta)) + param

    parser = mock.injection.require(Parser)

    cmd, args = parser.parse_command(["command", "42"])
    await mock.injection.call(cmd.func, named_args=args)

    assert value == 43


async def test_command_option() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    value = 0

    @command("command", "This is a test command", cache=cache)
    async def _(param: Annotated[int, Argument("option")]) -> None:
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    cmd, args = parser.parse_command(["command", "--param", "42"])
    await mock.injection.call(cmd.func, named_args=args)

    assert value == 42


async def test_command_option_flag() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    value = 0

    @command("command", "This is a test command", cache=cache)
    async def _(param: Annotated[int, Argument("option", "p")]):
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    cmd, args = parser.parse_command(["command", "-p", "42"])
    await mock.injection.call(cmd.func, named_args=args)

    assert value == 42


async def test_command_flag() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    value = False

    @command("command", "This is a test command", cache=cache)
    async def _(param: Annotated[Literal[True], Argument("option")]):
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    cmd, args = parser.parse_command(["command", "--param"])
    await mock.injection.call(cmd.func, named_args=args)

    assert value is True


async def test_command_flag_flag() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    value = False

    @command("command", "This is a test command", cache=cache)
    async def _(param: Annotated[Literal[True], Argument("option", "p")]):
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    cmd, args = parser.parse_command(["command", "-p"])
    await mock.injection.call(cmd.func, named_args=args)

    assert value is True


async def test_command_argument_help(capsys: CaptureFixture[Any]) -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    exited = False

    def _catch_exit(*_) -> None:
        nonlocal exited
        exited = True

    @command("command", "This is a test command", cache=cache)
    async def _(_: Annotated[int, Argument("option", "p", summary="This a help text for param arg")]):
        pass

    _exit = sys.exit
    sys.exit = _catch_exit

    parser = mock.injection.require(Parser)

    cmd, args = parser.parse_command(["command", "--help"])
    await mock.injection.call(cmd.func, named_args=args)

    assert exited

    assert "This a help text for param arg" in capsys.readouterr().out

    sys.exit = _exit


async def test_command_conflict() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    @command("command sub", "This is a test command", cache=cache)
    async def _() -> None:
        pass

    @command("command sub", "This is a test command", cache=cache)
    async def _() -> None:
        pass

    with pytest.raises(InitError) as info:
        mock.injection.require(Parser)

    assert "Conflict with 'command sub' command" in info.value.message


async def test_fail_non_nullable_positional_arg() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    @command("command sub", "This is a test command", cache=cache)
    async def _(p1: Annotated[str | None, Argument]) -> None:
        pass

    with pytest.raises(InitError) as info:
        mock.injection.require(Parser)

    assert (
        "Command test_fail_non_nullable_positional_arg.<locals>._, "
        "Argument 'p1', A positional argument cannot be nullable" == info.value.message
    )


async def test_command_arg_types() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    @command("command sub", "This is a test command", cache=cache)
    async def _(
        p1: Annotated[str, Argument],
        p2: Annotated[int, Argument],
        p3: Annotated[float, Argument],
        p4: Annotated[Literal[True], Argument],
        p5: Annotated[Literal[False], Argument],
        p6: Annotated[Literal[42], Argument],
        p7: Annotated[Literal[1, 2, 3], Argument],
        no_anno,  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
        p8: Annotated[Literal["one", "two"], Argument] = "one",
    ) -> None:
        pass

    mock.injection.require(Parser)


async def test_fail_wrong_arg_literal_type() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add_singleton(Parser)
    mock.mock(Logger[Parser])

    @command("command sub", "This is a test command", cache=cache)
    async def _(p1: Annotated[Literal[1, "two"], Argument]) -> None:
        pass

    with pytest.raises(InitError) as info:
        mock.injection.require(Parser)

    assert (
        "Command test_fail_wrong_arg_literal_type.<locals>._, "
        "Argument 'p1', Literal[1, two] is not a valid argument type" == info.value.message
    )
