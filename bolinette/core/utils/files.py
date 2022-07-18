from typing import Any
import yaml

from bolinette.core.utils import paths


def read_file(path) -> str | None:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def read_requirements(path) -> list[str]:
    try:
        with open(paths.join(path, "requirements.txt")) as f:
            return list(filter(lambda r: len(r), f.read().split("\n")))
    except FileNotFoundError:
        return []


def read_manifest(path, *, params: dict[str, Any] = None) -> dict | None:
    try:
        with open(paths.join(path, "manifest.blnt.yaml")) as f:
            raw = f.read()
            if params is not None:
                for param in params:
                    raw = raw.replace("{{" + str(param) + "}}", params[param])
            return yaml.safe_load(raw)
    except FileNotFoundError:
        return None
