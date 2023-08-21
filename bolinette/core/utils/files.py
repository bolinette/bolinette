from typing import Any

import yaml

from bolinette.core.utils import PathUtils


class FileUtils:
    def __init__(self, paths: PathUtils) -> None:
        self._paths = paths

    @staticmethod
    def read_file(path: str) -> str:
        with open(path) as f:
            return f.read()

    @staticmethod
    def read_yaml(path: str) -> dict[str, Any]:
        with open(path) as f:
            return yaml.safe_load(f)

    @staticmethod
    def read_requirements(path: str, *, name: str = "requirements.txt") -> list[str]:
        return list(
            filter(
                lambda r: len(r),
                FileUtils.read_file(PathUtils.join(path, name)).split("\n"),
            )
        )

    @staticmethod
    def read_profile(path: str) -> str | None:
        try:
            with open(PathUtils.join(path, ".profile")) as f:
                for line in f:
                    return line
        except FileNotFoundError:
            return None
        return None
