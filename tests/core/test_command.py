import sys

import pytest
from pytest import CaptureFixture

from bolinette import Cache, Logger, command, meta
from bolinette.command import Parser, _ArgumentMeta, _CommandMeta
from bolinette.exceptions import InitError
from bolinette.testing import Mock


def test_decorate_command() -> None:
    cache = Cache()

    @command("command", "This is a test command", cache=cache)
    async def _command() -> None:
        pass

    assert _CommandMeta in cache
    assert cache.get(_CommandMeta) == [_command]


def test_decorate_argument() -> None:
    @command.argument("argument", "p1")
    async def _command():
        pass

    assert meta.has(_command, _ArgumentMeta)
    assert len(meta.get(_command, _ArgumentMeta)) == 1
    assert meta.get(_command, _ArgumentMeta)[0].name == "p1"


async def test_launch_command() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
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

    _argv = sys.argv
    _exit = sys.exit
    sys.exit = _catch_exit  # type: ignore

    sys.argv = ["test", "command"]
    await parser.run()
    assert value == 2

    assert not exited

    sys.argv = _argv
    sys.exit = _exit


async def test_launch_command_not_found() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")

    value = 1

    exited = False

    def _catch_exit(*_) -> None:
        nonlocal exited
        exited = True

    error_str = ""

    def _write_error(s: str) -> None:
        nonlocal error_str
        error_str = s

    mock.mock(Logger[Parser]).setup(lambda l: l.error, _write_error)

    @command("command", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value += 1

    parser = mock.injection.require(Parser)

    _argv = sys.argv
    _exit = sys.exit
    sys.exit = _catch_exit  # type: ignore

    sys.argv = ["test", "none"]
    await parser.run()
    assert value == 1

    assert exited
    assert r"usage: test [-h] {command}" in error_str

    sys.argv = _argv
    sys.exit = _exit


async def test_launch_sub_command() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
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

    _argv = sys.argv
    _exit = sys.exit
    sys.exit = _catch_exit  # type: ignore

    sys.argv = ["test", "command", "inc"]
    await parser.run()
    assert value == 2

    sys.argv = ["test", "command", "dec"]
    await parser.run()
    assert value == 1

    assert not exited

    sys.argv = _argv
    sys.exit = _exit


async def test_launch_sub_command_not_found() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")

    value = 1

    exited = False

    def _catch_exit(*_) -> None:
        nonlocal exited
        exited = True

    error_str = ""

    def _write_error(s: str) -> None:
        nonlocal error_str
        error_str = s

    mock.mock(Logger[Parser]).setup(lambda l: l.error, _write_error)

    @command("command inc", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value += 1

    @command("command dec", "This is a test command", cache=cache)
    async def _() -> None:
        nonlocal value
        value -= 1

    parser = mock.injection.require(Parser)

    _argv = sys.argv
    _exit = sys.exit
    sys.exit = _catch_exit  # type: ignore
    sys.argv = ["test", "command", "none"]

    await parser.run()
    assert value == 1

    assert exited
    assert "usage: test command [-h] {inc,dec}" in error_str

    sys.argv = _argv
    sys.exit = _exit


async def test_command_argument() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
    mock.mock(Logger[Parser])

    _argv = sys.argv

    value = 0

    @command("command", "This is a test command", cache=cache)
    @command.argument("argument", "param", value_type=int)
    async def _(param: int):
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    sys.argv = ["test", "command", "42"]
    await parser.run()

    assert value == 42

    sys.argv = _argv


async def test_command_option() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
    mock.mock(Logger[Parser])

    _argv = sys.argv

    value = 0

    @command("command", "This is a test command", cache=cache)
    @command.argument("option", "param", value_type=int)
    async def _(param: int):
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    sys.argv = ["test", "command", "--param", "42"]
    await parser.run()

    assert value == 42

    sys.argv = _argv


async def test_command_option_flag() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
    mock.mock(Logger[Parser])

    _argv = sys.argv

    value = 0

    @command("command", "This is a test command", cache=cache)
    @command.argument("option", "param", value_type=int, flag="p")
    async def _(param: int):
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    sys.argv = ["test", "command", "-p", "42"]
    await parser.run()

    assert value == 42

    sys.argv = _argv


async def test_command_flag() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
    mock.mock(Logger[Parser])

    _argv = sys.argv

    value = False

    @command("command", "This is a test command", cache=cache)
    @command.argument("flag", "param")
    async def _(param: bool):
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    sys.argv = ["test", "command", "--param"]
    await parser.run()

    assert value

    sys.argv = _argv


async def test_command_flag_flag() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
    mock.mock(Logger[Parser])

    _argv = sys.argv

    value = False

    @command("command", "This is a test command", cache=cache)
    @command.argument("flag", "param", flag="p")
    async def _(param: bool):
        nonlocal value
        value = param

    parser = mock.injection.require(Parser)

    sys.argv = ["test", "command", "-p"]
    await parser.run()

    assert value

    sys.argv = _argv


async def test_command_argument_help(capsys: CaptureFixture) -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
    mock.mock(Logger[Parser])

    exited = False

    def _catch_exit(*_) -> None:
        nonlocal exited
        exited = True

    @command("command", "This is a test command", cache=cache)
    @command.argument("flag", "param", flag="p", summary="This a help text for param arg")
    async def _(param: bool):
        pass

    _argv = sys.argv
    _exit = sys.exit
    sys.exit = _catch_exit  # type: ignore

    parser = mock.injection.require(Parser)

    sys.argv = ["test", "command", "--help"]
    await parser.run()

    assert exited

    assert "This a help text for param arg" in capsys.readouterr().out

    sys.argv = _argv
    sys.exit = _exit


async def test_command_conflict() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.injection.add(Parser, "singleton")
    mock.mock(Logger[Parser])

    @command("command sub", "This is a test command", cache=cache)
    async def _() -> None:
        pass

    @command("command sub", "This is a test command", cache=cache)
    async def _() -> None:
        pass

    parser = mock.injection.require(Parser)

    _argv = sys.argv

    sys.argv = ["test", "command", "--help"]
    with pytest.raises(InitError) as info:
        await parser.run()

    assert "Conflict with 'command sub' command" in info.value.message  # type: ignore

    sys.argv = _argv
