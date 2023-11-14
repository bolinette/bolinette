import inspect
import re
import sys
import tomllib
from ctypes import ArgumentError
from pathlib import Path
from types import ModuleType
from typing import Any

from bolinette import core, data, web


def parse_pyproject(path: Path) -> dict[str, Any]:
    with open(path / "pyproject.toml", "rb") as file:
        return tomllib.load(file)


def get_version(module: ModuleType) -> str:
    module_path = Path(inspect.getfile(module)).parent
    config = parse_pyproject(module_path)
    return config["tool"]["poetry"]["version"]


def update_version(path: Path, major: int, minor: int, patch: int) -> None:
    with open(path, "r") as stream:
        content = stream.read()
    content = re.sub(r'version = "[^"]+"', f'version = "{major}.{minor}.{patch}"', content, 1)
    with open(path, "w") as stream:
        stream.write(content)


def update_module_version(module: ModuleType, major: int, minor: int, patch: int) -> None:
    pyproject_path = Path(inspect.getfile(module)).parent / "pyproject.toml"
    update_version(pyproject_path, major, minor, patch)


def update_requirements(module: ModuleType, name: str, version: str) -> None:
    pyproject_path = Path(inspect.getfile(module)).parent / "pyproject.toml"
    with open(pyproject_path, "r") as stream:
        content = stream.read()
    content = re.sub(rf'{name} = "\^[^"]+"', f'{name} = "^{version}"', content, 1)
    with open(pyproject_path, "w") as stream:
        stream.write(content)


def update_core(major: int, minor: int, patch: int) -> None:
    update_module_version(core, major, minor, patch)
    update_version(Path("pyproject.toml"), major, minor, patch)


def update_data(major: int, minor: int, patch: int) -> None:
    update_module_version(data, major, minor, patch)
    update_requirements(data, "bolinette", get_version(core))


def update_web(major: int, minor: int, patch: int) -> None:
    update_module_version(web, major, minor, patch)
    update_requirements(web, "bolinette", get_version(core))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise ArgumentError("Only accepts 3 argument")
    project = sys.argv[1]
    version = sys.argv[2]
    if not (match := re.match(r"(\d+)\.(\d+).(\d+)", version)):
        raise ArgumentError("Invalid version format")
    match project:
        case "core":
            update_core(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        case "data":
            update_data(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        case "web":
            update_web(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        case _:
            raise ArgumentError("Unknown package")
