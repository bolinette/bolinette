import asyncio
import importlib
import inspect
import sys
import tomllib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast

from bolinette.core._bolinette import Bolinette, make_bolinette
from bolinette.core.commands.exceptions import CommandError, CommandUsageError
from bolinette.core.exceptions import BolinetteError, InitError

type AppFactory = Callable[[], Bolinette | Awaitable[Bolinette]]

PYPROJECT_FILE = "pyproject.toml"
FACTORY_SETTING = "app_factory"


def load_app_factory(project_dir: Path | None = None) -> AppFactory:
    project_dir = project_dir if project_dir is not None else Path.cwd()
    settings = _read_bolinette_settings(project_dir / PYPROJECT_FILE)
    if settings is None:
        return make_bolinette
    if FACTORY_SETTING not in settings:
        raise InitError(f"Key 'tool.bolinette.{FACTORY_SETTING}' is undefined in {PYPROJECT_FILE}")
    return _import_factory(str(settings[FACTORY_SETTING]))


def _read_bolinette_settings(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, "rb") as file:
            manifest = tomllib.load(file)
    except FileNotFoundError:
        return None
    settings = manifest.get("tool", {}).get("bolinette")
    return settings if isinstance(settings, dict) else None  # pyright: ignore[reportUnknownVariableType]


def _import_factory(path: str) -> AppFactory:
    module_name, _, attr = path.partition(":")
    if not module_name or not attr:
        raise InitError(f"Setting '{FACTORY_SETTING}' in {PYPROJECT_FILE} must be like 'path.to.module:factory_func'")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as err:
        raise InitError(
            f"Module '{module_name}' does not exist, check the '{FACTORY_SETTING}' setting in {PYPROJECT_FILE}"
        ) from err
    factory: Any = getattr(module, attr, None)
    if not callable(factory):
        raise InitError(f"'{module_name}' has no callable '{attr}', check the '{FACTORY_SETTING}' setting")
    return cast(AppFactory, factory)


async def build_app(factory: AppFactory) -> Bolinette:
    result = factory()
    blnt = await result if inspect.isawaitable(result) else result
    if not isinstance(blnt, Bolinette):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise InitError(f"Factory '{factory.__qualname__}' did not return a Bolinette instance")
    return blnt


async def run(args: list[str], project_dir: Path | None = None) -> int:
    blnt = await build_app(load_app_factory(project_dir))
    try:
        return await blnt.run_command(args) or 0
    finally:
        await blnt.dispose()


def main(argv: list[str] | None = None) -> None:
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    args = sys.argv[1:] if argv is None else argv
    try:
        code = asyncio.run(run(args))
    except CommandError as err:
        print(err.message, file=sys.stderr if isinstance(err, CommandUsageError) else sys.stdout)
        code = err.code
    except BolinetteError as err:
        print(err.message, file=sys.stderr)
        code = 1
    sys.exit(code)


if __name__ == "__main__":  # pragma: no cover
    main()
