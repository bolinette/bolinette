import inspect
import os
import re
import sys
from ctypes import ArgumentError
from typing import Any

from bolinette import core, data, web


def update_version(module: Any, major: int, minor: int, patch: int) -> None:
    version = f"{major}.{minor}.{patch}"
    file = os.path.join(os.path.dirname(inspect.getfile(module)), "version.py")
    with open(file, 'w') as stream:
        stream.write(f'__version__ = "{version}"\n')


def update_requirements(file: str, name: str, version: str) -> None:
    with open(file, 'r') as stream:
        content = stream.read()
    content = re.sub(rf"{name}==(\d+)\.(\d+).(\d+)", f"{name}=={version}", content, 1)
    with open(file, 'w') as stream:
        stream.write(content)


def update_core(major: int, minor: int, patch: int) -> None:
    update_version(core, major, minor, patch)


def update_data(major: int, minor: int, patch: int) -> None:
    update_version(data, major, minor, patch)
    update_requirements("requirements.data.txt", "bolinette", core.__version__)


def update_web(major: int, minor: int, patch: int) -> None:
    update_version(web, major, minor, patch)
    update_requirements("requirements.web.txt", "bolinette-data", data.__version__)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise ArgumentError("Only accepts 1 argument")
    tag = sys.argv[1]
    try:
        project, version = tag.split("-")
    except ValueError:
        raise ArgumentError("Invalid version format")
    if not (match := re.match(r"(\d+)\.(\d+).(\d+)", version)):
        raise ArgumentError("Invalid version format")
    match (project):
        case "core":
            update_core(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        case "data":
            update_data(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        case "web":
            update_web(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        case _:
            raise ArgumentError("Unknown package")