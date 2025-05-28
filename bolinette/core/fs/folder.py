from pathlib import Path
from typing import Any, override

from bolinette.core.fs import FSFile, FSNode, FSYamlFile


class FSFolder(FSNode):
    def __init__(self, path: Path, parent: "FSFolder | None" = None) -> None:
        super().__init__(path, parent)
        self.children: list[FSNode] = []
        if self.exists():
            self.children = [FSFolder._to_node(child, self) for child in self.path.iterdir()]
        else:
            self.children = []

    @staticmethod
    def _to_node(path: Path, parent: "FSFolder | None") -> FSNode:
        if path.name.endswith(".yml") or path.name.endswith(".yaml"):
            return FSYamlFile(path, parent)
        if path.is_dir():
            return FSFolder(path, parent)
        else:
            return FSFile(path, parent)

    def __getitem__(self, child_name: str) -> FSNode:
        for child in self.children:
            if child.path.name == child_name:
                return child
        raise KeyError(f"Child node {child_name} not found in {self.path}")

    def __contains__(self, child_name: str) -> bool:
        for child in self.children:
            if child.path.name == child_name:
                return True
        return False

    def find(self, path: Path) -> FSNode | None:
        parts = path.parts
        part = parts[0]
        for child in self.children:
            if child.path.name == part:
                if len(parts) == 1:
                    return child
                if isinstance(child, FSFolder):
                    return child.find(Path(*parts[1:]))
                return None
        return None

    def add_file(self, name: str) -> FSFile:
        if name in self:
            file = self[name]
            if not FSNode.is_file(file):
                raise TypeError(f"Path {file.path} is not a file.")
            return file
        file = FSFile(self.path / name, self)
        self.children.append(file)
        return file

    def add_yaml_file(self, name: str) -> FSYamlFile:
        if name in self:
            file = self[name]
            if not FSNode.is_yaml_file(file, Any):  # pyright: ignore
                raise TypeError(f"Path {file.path} is not yaml a file.")
            return file  # pyright: ignore
        file = FSYamlFile(self.path / name, self)
        self.children.append(file)
        return file

    def add_folder(self, name: str) -> "FSFolder":
        if name in self:
            folder = self[name]
            if not FSNode.is_folder(folder):
                raise TypeError(f"Path {folder.path} is not a folder.")
            return folder
        folder = FSFolder(self.path / name, self)
        self.children.append(folder)
        return folder

    def is_package(self) -> bool:
        return "__init__.py" in self

    def init_package(self) -> FSFile:
        if not self.is_package():
            return self.add_file("__init__.py")
        dunder_init = self["__init__.py"]
        if not FSNode.is_file(dunder_init):
            raise TypeError(f"Path {dunder_init.path} is not a file.")
        return dunder_init

    @override
    def commit(self) -> None:
        self.path.mkdir(exist_ok=True, parents=True)
        for child in self.children:
            child.commit()
