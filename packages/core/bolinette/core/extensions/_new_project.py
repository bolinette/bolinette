from collections.abc import Callable
from dataclasses import dataclass

from bolinette.core.extensions._extensions import Extension
from bolinette.core.fs import FSFolder


@dataclass(frozen=True, slots=True)
class ExtensionSource:
    module: str
    attr: str

    @property
    def import_line(self) -> str:
        return f"from {self.module} import {self.attr}"


@dataclass
class NewProjectHookContext:
    name: str
    extensions: list[Extension]
    extension_names: list[str]
    extension_sources: list[ExtensionSource]
    dependencies: list[str]
    project_folder: FSFolder
    package_folder: FSFolder
    on_failure: Callable[[int], None]
