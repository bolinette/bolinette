from pathlib import Path
from typing import override

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
