from pathlib import Path
from typing import Any, override

import yaml

from bolinette.core import fs


class FSFile(fs.FSNode):
    def __init__(self, path: Path, parent: "fs.FSFolder | None" = None) -> None:
        super().__init__(path, parent)
        self.lines: list[str]
        if self.exists():
            self.lines = self.path.read_text().splitlines()
            self.touched = False
        else:
            self.lines = []
            self.touched = True

    def append(self, *lines: str) -> None:
        self.lines = [*self.lines, *lines]
        self.touched = True

    def prepend(self, *lines: str) -> None:
        self.lines = [*lines, *self.lines]
        self.touched = True

    @override
    def commit(self) -> None:
        if not self.touched:
            return
        if self.lines:
            self.path.write_text("\n".join(self.lines) + "\n")
        else:
            self.path.touch()


class FSYamlFile(FSFile):
    def __init__(self, path: Path, parent: "fs.FSFolder | None" = None) -> None:
        super().__init__(path, parent)
        if self.exists():
            with open(self.path) as file:
                self.content = yaml.safe_load(file)
        else:
            self.content: Any | None = None

    @override
    def append(self, *lines: str) -> None:
        raise NotImplementedError("YamlFile does not support appending lines.")

    @override
    def prepend(self, *lines: str) -> None:
        raise NotImplementedError("YamlFile does not support prepending lines.")

    @override
    def commit(self) -> None:
        if not self.touched:
            return
        self.path.write_text(yaml.safe_dump(self.content, sort_keys=False))
