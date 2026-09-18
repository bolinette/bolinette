"""The `blnt` entry point: locating the application factory and running a command."""

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from escondite import Cache

from bolinette.core import Bolinette, load_app_factory, make_bolinette
from bolinette.core.__main__ import build_app, main, run
from bolinette.core.commands import command
from bolinette.core.exceptions import BolinetteError, InitError


def _write_pyproject(folder: Path, factory: str | None) -> None:
    lines = ["[tool.bolinette]"]
    if factory is not None:
        lines.append(f'app_factory = "{factory}"')
    (folder / "pyproject.toml").write_text("\n".join(lines) + "\n")


@pytest.fixture
def project(tmp_cwd: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A temporary project directory that is importable, with a `myapp` module defining factories."""
    monkeypatch.syspath_prepend(str(tmp_cwd))  # pyright: ignore[reportUnknownMemberType]
    (tmp_cwd / "myapp.py").write_text(
        "from bolinette.core import make_bolinette\n"
        "\n"
        "async def factory():\n"
        "    return await make_bolinette()\n"
        "\n"
        "def not_callable():\n"
        "    return 1\n"
        "\n"
        "not_a_function = 1\n"
        "\n"
        "def wrong_type():\n"
        "    return 1\n"
    )
    yield tmp_cwd
    sys.modules.pop("myapp", None)


class TestLoadAppFactory:
    def test_without_pyproject_returns_default_factory(self, tmp_cwd: Path) -> None:
        """Without a `pyproject.toml` the core-only `make_bolinette` is used."""
        assert load_app_factory() is make_bolinette

    def test_without_bolinette_table_returns_default_factory(self, tmp_cwd: Path) -> None:
        """A `pyproject.toml` without a `tool.bolinette` table falls back on the default factory."""
        (tmp_cwd / "pyproject.toml").write_text('[project]\nname = "x"\n')

        assert load_app_factory() is make_bolinette

    def test_explicit_project_dir(self, project: Path, tmp_path: Path) -> None:
        """The project directory can be given instead of using the current one."""
        other = tmp_path / "other"
        other.mkdir()
        _write_pyproject(other, "myapp:factory")

        factory = load_app_factory(other)

        assert factory.__name__ == "factory"

    def test_missing_setting_raises(self, project: Path) -> None:
        """A `tool.bolinette` table without `app_factory` is an error."""
        _write_pyproject(project, None)

        with pytest.raises(InitError, match="app_factory"):
            load_app_factory()

    def test_malformed_path_raises(self, project: Path) -> None:
        """The setting must be a `module:attribute` path."""
        _write_pyproject(project, "myapp.factory")

        with pytest.raises(InitError, match=r"path\.to\.module:factory_func"):
            load_app_factory()

    def test_unknown_module_raises(self, project: Path) -> None:
        """A module that cannot be imported is reported."""
        _write_pyproject(project, "nope_module:factory")

        with pytest.raises(InitError, match="does not exist"):
            load_app_factory()

    def test_missing_attribute_raises(self, project: Path) -> None:
        """An attribute that does not exist on the module is reported."""
        _write_pyproject(project, "myapp:missing")

        with pytest.raises(InitError, match="no callable 'missing'"):
            load_app_factory()

    def test_non_callable_attribute_raises(self, project: Path) -> None:
        """An attribute that is not callable is reported."""
        _write_pyproject(project, "myapp:not_a_function")

        with pytest.raises(InitError, match="no callable"):
            load_app_factory()


class TestBuildApp:
    async def test_async_factory(self, tmp_cwd: Path) -> None:
        """A coroutine factory is awaited."""
        blnt = await build_app(make_bolinette)

        assert isinstance(blnt, Bolinette)
        await blnt.dispose()

    async def test_sync_factory(self, tmp_cwd: Path) -> None:
        """A plain factory returning an application is accepted."""
        built = await make_bolinette()

        blnt = await build_app(lambda: built)

        assert blnt is built
        await blnt.dispose()

    async def test_wrong_return_type_raises(self, tmp_cwd: Path) -> None:
        """A factory that does not return a `Bolinette` is reported."""

        def wrong() -> Bolinette:
            return 1  # pyright: ignore[reportReturnType]

        with pytest.raises(InitError, match="did not return a Bolinette"):
            await build_app(wrong)


class TestRun:
    async def test_runs_command_and_returns_its_code(self, project: Path) -> None:
        """`run` builds the application, runs the command and returns its exit code."""
        _write_pyproject(project, "myapp:factory")

        @command("hello", "Says hello")
        async def hello() -> int:
            return 7

        try:
            assert await run(["hello"]) == 7
        finally:
            Cache.with_fallback(None).clear()

    async def test_none_exit_code_becomes_zero(self, project: Path) -> None:
        """A command returning nothing yields exit code 0."""
        _write_pyproject(project, "myapp:factory")

        @command("hello", "Says hello")
        async def hello() -> None:
            pass

        try:
            assert await run(["hello"]) == 0
        finally:
            Cache.with_fallback(None).clear()

    async def test_app_is_disposed_after_command(self, project: Path) -> None:
        """The application is disposed once the command has run, even when it fails."""
        _write_pyproject(project, "myapp:factory")

        @command("boom", "Fails")
        async def boom() -> None:
            raise RuntimeError("boom")

        try:
            with pytest.raises(RuntimeError, match="boom"):
                await run(["boom"])
        finally:
            Cache.with_fallback(None).clear()


class TestMain:
    def test_exit_code_is_forwarded(self, tmp_cwd: Path) -> None:
        """`main` exits with the command exit code."""

        @command("hello", "Says hello")
        async def hello() -> int:
            return 4

        try:
            with pytest.raises(SystemExit) as info:
                main(["hello"])
        finally:
            Cache.with_fallback(None).clear()

        assert info.value.code == 4

    def test_init_error_is_printed(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """An `InitError` is printed on stderr and turns into exit code 1."""
        _write_pyproject(project, "myapp:missing")

        with pytest.raises(SystemExit) as info:
            main(["hello"])

        assert info.value.code == 1
        assert "no callable 'missing'" in capsys.readouterr().err

    def test_bolinette_error_is_printed(self, tmp_cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Any `BolinetteError` raised by a command is printed on stderr with exit code 1."""

        class CustomError(BolinetteError):
            pass

        @command("fail", "Fails")
        async def fail() -> None:
            raise CustomError("something went wrong")

        try:
            with pytest.raises(SystemExit) as info:
                main(["fail"])
        finally:
            Cache.with_fallback(None).clear()

        assert info.value.code == 1
        assert capsys.readouterr().err.strip() == "something went wrong"

    def test_other_exceptions_propagate(self, tmp_cwd: Path) -> None:
        """An unexpected exception is not swallowed, so the traceback reaches the developer."""

        @command("boom", "Fails")
        async def boom() -> None:
            raise RuntimeError("boom")

        try:
            with pytest.raises(RuntimeError, match="boom"):
                main(["boom"])
        finally:
            Cache.with_fallback(None).clear()

    def test_help_goes_to_stdout_with_code_zero(self, tmp_cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """`--help` prints the help on stdout and exits with 0."""
        with pytest.raises(SystemExit) as info:
            main(["--help"])

        out, err = capsys.readouterr()
        assert info.value.code == 0
        assert "Bolinette Framework" in out
        assert err == ""

    def test_missing_command_prints_help_with_code_one(self, tmp_cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """No command prints the help on stdout and exits with 1."""
        with pytest.raises(SystemExit) as info:
            main([])

        assert info.value.code == 1
        assert "Bolinette Framework" in capsys.readouterr().out

    def test_usage_error_goes_to_stderr_with_code_two(self, tmp_cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """A bad command line prints the usage error on stderr and exits with 2."""
        with pytest.raises(SystemExit) as info:
            main(["nope"])

        out, err = capsys.readouterr()
        assert info.value.code == 2
        assert out == ""
        assert err.startswith("usage:")
        assert "invalid choice: 'nope'" in err

    def test_cwd_is_added_to_sys_path(self, tmp_cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The current directory is made importable so that the project module can be loaded."""
        monkeypatch.setattr(sys, "path", [p for p in sys.path if p != str(tmp_cwd)])

        with pytest.raises(SystemExit):
            main(["--help"])

        assert str(tmp_cwd) in sys.path

    def test_module_is_runnable(self, tmp_cwd: Path) -> None:
        """`python -m bolinette.core` runs the CLI."""
        result = subprocess.run(
            [sys.executable, "-m", "bolinette.core", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "Bolinette Framework" in result.stdout
