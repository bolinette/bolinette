import asyncio
import importlib
import re
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bolinette.core import Bolinette


def main() -> None:
    cwd = Path.cwd()
    if cwd not in sys.path:
        sys.path.append(str(cwd))

    manifest = _parse_pyprojet_toml()
    blnt: Bolinette | None = None
    if "tool" in manifest and "bolinette" in manifest["tool"]:
        if "app_factory" not in manifest["tool"]["bolinette"]:
            raise RuntimeError("Key 'tool.bolinette.app_factory' is undefined in pyproject.toml")
        factory_path = manifest["tool"]["bolinette"]["app_factory"]
        if not (match := _FACTORY_PATH_REGEX.match(factory_path)):
            raise RuntimeError("Setting 'app_factory' in pyproject.toml must be like 'path.to.module:factory_func'")
        blnt = _import_bolinette(match.group(1), match.group(2))
    if blnt is None:
        blnt = Bolinette()
    asyncio.run(blnt.exec_args(sys.argv[1:]))


def _parse_pyprojet_toml() -> dict[str, Any]:
    try:
        with open("pyproject.toml", "rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        return {}


def _import_bolinette(path: str, func: str) -> Bolinette:
    try:
        module = importlib.import_module(path)
        factory: Callable[[], Any] = getattr(module, func)
        blnt = factory()
    except ModuleNotFoundError as err:
        raise RuntimeError(
            f"Module '{path}' does not exist. Please check the 'app_factory' setting in pyproject.toml"
        ) from err
    except AttributeError as err:
        raise RuntimeError(
            f"'{path}' has no attributes '{func}'. Please check the 'app_factory' setting in pyproject.toml"
        ) from err
    except TypeError as err:
        raise RuntimeError(f"Could not call factory function '{func}', the signature must be empty.") from err
    if not isinstance(blnt, Bolinette):
        raise RuntimeError(f"Factory function '{func}' did not return an instance of Bolinette.")
    return blnt


_FACTORY_PATH_REGEX = re.compile(r"([^:]+):(.+)")

if __name__ == "__main__":
    main()
