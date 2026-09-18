"""Injectable loggers configured from the core environment section."""

import logging
import logging.handlers
from pathlib import Path

from escondite import Cache

from bolinette.core import Logger, startup
from bolinette.core._logging import BasicFormatter, ColorFormatter
from tests.core.conftest import AppFactory


def _write_logging(env_folder: Path, *entries: str) -> None:
    (env_folder / "env.toml").write_text("".join(f"[[core.logging]]\n{entry}\n" for entry in entries))


class TestLoggerInjection:
    async def test_logger_is_injectable(self, make_app: AppFactory, cache: Cache) -> None:
        """`Logger[T]` resolves to a standard logger named after `T`."""

        class InjectionTarget:
            pass

        seen: list[Logger[InjectionTarget]] = []

        @startup(cache=cache)
        async def init(logger: Logger[InjectionTarget]) -> None:
            seen.append(logger)

        blnt = await make_app()
        await blnt.startup()

        assert isinstance(seen[0], logging.Logger)
        assert "InjectionTarget" in seen[0].name

    async def test_same_type_yields_same_logger(self, make_app: AppFactory, cache: Cache) -> None:
        """Requiring the logger of the same type twice does not add handlers twice."""

        class SharedTarget:
            pass

        seen: list[Logger[SharedTarget]] = []

        @startup(cache=cache)
        async def init(first: Logger[SharedTarget], second: Logger[SharedTarget]) -> None:
            seen.extend([first, second])

        blnt = await make_app()
        await blnt.startup()

        assert seen[0] is seen[1]
        assert len(seen[0].handlers) == 1

    async def test_default_configuration(self, make_app: AppFactory, cache: Cache) -> None:
        """Without configuration a colored stderr handler at level INFO is attached."""

        class DefaultTarget:
            pass

        seen: list[Logger[DefaultTarget]] = []

        @startup(cache=cache)
        async def init(logger: Logger[DefaultTarget]) -> None:
            seen.append(logger)

        blnt = await make_app()
        await blnt.startup()

        (handler,) = seen[0].handlers
        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logging.INFO
        assert isinstance(handler.formatter, ColorFormatter)

    async def test_debug_lowers_the_default_level(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """With `debug = true` and no logging table, the default handler logs at DEBUG."""
        (env_folder / "env.toml").write_text("[core]\ndebug = true\n")

        class DebugTarget:
            pass

        seen: list[Logger[DebugTarget]] = []

        @startup(cache=cache)
        async def init(logger: Logger[DebugTarget]) -> None:
            seen.append(logger)

        blnt = await make_app()
        await blnt.startup()

        (handler,) = seen[0].handlers
        assert handler.level == logging.DEBUG
        assert isinstance(handler.formatter, ColorFormatter)

    async def test_stream_configuration(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """A stderr entry sets the handler level and formatter."""
        _write_logging(env_folder, 'type = "stderr"\nlevel = "DEBUG"\ncolor = false')

        class StreamTarget:
            pass

        seen: list[Logger[StreamTarget]] = []

        @startup(cache=cache)
        async def init(logger: Logger[StreamTarget]) -> None:
            seen.append(logger)

        blnt = await make_app()
        await blnt.startup()

        (handler,) = seen[0].handlers
        assert handler.level == logging.DEBUG
        assert isinstance(handler.formatter, BasicFormatter)

    async def test_file_configuration(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """A file entry attaches a rotating file handler and creates the parent folder."""
        _write_logging(env_folder, 'type = "file"\nlevel = "WARNING"\npath = "logs/app.log"')

        class FileTarget:
            pass

        seen: list[Logger[FileTarget]] = []

        @startup(cache=cache)
        async def init(logger: Logger[FileTarget]) -> None:
            seen.append(logger)

        blnt = await make_app()
        await blnt.startup()

        (handler,) = seen[0].handlers
        assert isinstance(handler, logging.handlers.TimedRotatingFileHandler)
        assert handler.level == logging.WARNING
        assert (env_folder.parent / "logs").is_dir()
        handler.close()

    async def test_multiple_entries(self, make_app: AppFactory, cache: Cache, env_folder: Path) -> None:
        """Every configured entry adds one handler."""
        _write_logging(
            env_folder,
            'type = "stderr"\nlevel = "INFO"',
            'type = "stderr"\nlevel = "ERROR"',
        )

        class MultiTarget:
            pass

        seen: list[Logger[MultiTarget]] = []

        @startup(cache=cache)
        async def init(logger: Logger[MultiTarget]) -> None:
            seen.append(logger)

        blnt = await make_app()
        await blnt.startup()

        assert [h.level for h in seen[0].handlers] == [logging.INFO, logging.ERROR]


class TestFormatters:
    def test_basic_format(self) -> None:
        """The basic formatter prints the timestamp, level, service name and message."""
        record = logging.LogRecord("x", logging.INFO, "f.py", 1, "hello %s", ("world",), None)

        line = BasicFormatter("svc").format(record)

        assert line.endswith(" [INFO] <svc> hello world")
        assert line[:4].isdigit()

    def test_color_format(self) -> None:
        """The color formatter wraps the level and service name in escape codes."""
        record = logging.LogRecord("x", logging.ERROR, "f.py", 1, "boom", None, None)

        line = ColorFormatter("svc").format(record)

        assert "\x1b[31mERROR\x1b[0m" in line
        assert "<\x1b[32msvc\x1b[0m> boom" in line
