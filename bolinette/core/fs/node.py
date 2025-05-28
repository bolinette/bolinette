from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeGuard

from bolinette.core import fs


class FSNode(ABC):
    def __init__(self, path: Path, parent: "fs.FSFolder | None" = None) -> None:
        self.path = path
        self.parent = parent

    def exists(self) -> bool:
        return self.path.exists()

    @staticmethod
    def is_file(node: "FSNode") -> "TypeGuard[fs.FSFile]":
        return isinstance(node, fs.FSFile)

    @staticmethod
    def is_yaml_file(node: "FSNode") -> "TypeGuard[fs.FSYamlFile]":
        return isinstance(node, fs.FSYamlFile)

    @staticmethod
    def is_folder(node: "FSNode") -> "TypeGuard[fs.FSFolder]":
        return isinstance(node, fs.FSFolder)

    @abstractmethod
    def commit(self) -> None: ...
