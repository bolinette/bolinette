from pathlib import Path

from setuptools import find_namespace_packages


def read_file(path: Path) -> str:
    with open(path) as f:
        return f.read()


def read_requirements(path: Path) -> list[str]:
    return [s for s in read_file(path).splitlines() if len(s)]


def project_packages(module: str) -> list[str]:
    return [m for m in find_namespace_packages() if m.startswith(module)]
