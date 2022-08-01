from typing import Any

import yaml

from bolinette.core.utils import paths


class FileUtils:
    def __init__(self, paths: paths.PathUtils) -> None:
        self._paths = paths

    @staticmethod
    def read_file(path: str) -> str | None:
        try:
            with open(path) as f:
                return f.read()
        except FileNotFoundError:
            return None

    @staticmethod
    def read_yaml(path: str) -> dict | None:
        try:
            with open(path) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return None

    def read_requirements(self, path: str) -> list[str]:
        try:
            with open(self._paths.join(path, "requirements.txt")) as f:
                return list(filter(lambda r: len(r), f.read().split("\n")))
        except FileNotFoundError:
            return []

    def read_profile(self, path: str) -> str | None:
        try:
            with open(self._paths.join(path, ".profile")) as f:
                for line in f:
                    return line
        except FileNotFoundError:
            return None
        return None

    def read_manifest(self, path: str, *, params: dict[str, Any] = None) -> dict | None:
        try:
            with open(self._paths.join(path, "manifest.blnt.yaml")) as f:
                raw = f.read()
                if params is not None:
                    for param in params:
                        raw = raw.replace("{{" + str(param) + "}}", params[param])
                return yaml.safe_load(raw)
        except FileNotFoundError:
            return None
