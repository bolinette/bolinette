from typing import Any

import yaml

from bolinette.core.utils import paths


class FileUtils:
    def __init__(self, paths: paths.PathUtils) -> None:
        self._paths = paths

    @staticmethod
    def read_file(path: str) -> str:
        with open(path) as f:
            return f.read()

    @staticmethod
    def read_yaml(path: str) -> dict[str, Any]:
        with open(path) as f:
            return yaml.safe_load(f)

    def read_requirements(self, path: str, *, name: str = "requirements.txt") -> list[str]:
        return list(
            filter(
                lambda r: len(r),
                self.read_file(self._paths.join(path, name)).split("\n"),
            )
        )

    def read_profile(self, path: str) -> str | None:
        try:
            with open(self._paths.join(path, ".profile")) as f:
                for line in f:
                    return line
        except FileNotFoundError:
            return None
        return None
