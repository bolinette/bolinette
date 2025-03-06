import inspect
import os
import re
import sys
import tomllib
from ctypes import ArgumentError
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, override

from bolinette import api, core, data, web


@dataclass
class Version:
    major: int
    minor: int
    patch: int

    @override
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_pyproject(path: Path) -> dict[str, Any]:
    with open(path / "pyproject.toml", "rb") as file:
        return tomllib.load(file)


def get_project_name(module: ModuleType) -> str:
    module_path = Path(inspect.getfile(module)).parent
    config = parse_pyproject(module_path)
    return config["tool"]["poetry"]["name"]


def get_version(module: ModuleType) -> str:
    module_path = Path(inspect.getfile(module)).parent
    config = parse_pyproject(module_path)
    return config["tool"]["poetry"]["version"]


def update_version(path: Path, version: Version) -> None:
    with open(path) as stream:
        content = stream.read()
    content = re.sub(r'version = "[^"]+"', f'version = "{version}"', content, count=1)
    with open(path, "w") as stream:
        stream.write(content)


def update_module_version(module: ModuleType, version: Version) -> None:
    pyproject_path = Path(inspect.getfile(module)).parent / "pyproject.toml"
    update_version(pyproject_path, version)


def update_requirements(module: ModuleType, name: str, version: str) -> None:
    pyproject_path = Path(inspect.getfile(module)).parent / "pyproject.toml"
    with open(pyproject_path) as stream:
        content = stream.read()
    content = re.sub(rf'{name} = "\^[^"]+"', f'{name} = "^{version}"', content, count=1)
    with open(pyproject_path, "w") as stream:
        stream.write(content)


def update_core(version: Version) -> None:
    update_module_version(core, version)
    update_version(Path("pyproject.toml"), version)
    log_update("core", version)


def update_data(version: Version) -> None:
    update_module_version(data, version)
    update_requirements(data, get_project_name(core), get_version(core))
    log_update("data", version)


def update_web(version: Version) -> None:
    update_module_version(web, version)
    update_requirements(web, get_project_name(core), get_version(core))
    log_update("web", version)


def update_api(version: Version) -> None:
    update_module_version(api, version)
    update_requirements(api, get_project_name(data), get_version(data))
    update_requirements(api, get_project_name(web), get_version(web))
    log_update("api", version)


def log(message: str, *, indent: int = 0) -> None:
    print(" " * indent + message, file=sys.stderr)


def log_update(project: str, version: Version) -> None:
    log(f"Updated {project} to version {version}")


def check_git_clean() -> None:
    if os.system("git diff --quiet") != 0:
        raise RuntimeError("Git repository is not clean")


def create_git_commit(projects: list[str], version: Version) -> None:
    log(f"Committing changes for updating {join_with_and(projects)} to {version}")
    os.system("git add -A")
    os.system(f"git commit -m '[global] Updated {join_with_and(projects)} to {version}'")


def create_git_tag(project: str, version: Version) -> None:
    tag = f"{project}-{version}"
    log(f"Creating tag {tag} for {project}")
    os.system(f"git tag {tag}")


def join_with_and(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def main(argv: list[str]) -> None:
    check_git_clean()

    if len(argv) < 2:
        raise ArgumentError("Must at least provide a package and a version")

    projects = argv[:-1]

    version = argv[-1]
    if not re.match(r"(\d+)\.(\d+).(\d+)", version):
        raise ArgumentError("Invalid version format")
    version = Version(*map(int, version.split(".")))

    if projects == ["all"]:
        projects = ["core", "data", "web", "api"]

    for project in projects:
        match project:
            case "core":
                update_core(version)
            case "data":
                update_data(version)
            case "web":
                update_web(version)
            case "api":
                update_api(version)
            case _:
                raise ArgumentError("Unknown package")

    create_git_commit(projects, version)

    for project in projects:
        create_git_tag(project, version)


if __name__ == "__main__":
    main(sys.argv[1:])
