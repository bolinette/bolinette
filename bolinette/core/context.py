from typing import Any
from collections.abc import Iterable

from bolinette import abc, core, web, mapping, BolinetteExtension, Extensions
from bolinette.core.database import DatabaseManager
from bolinette.utils import files


class BolinetteContext(abc.Context):
    def __init__(self, origin: str, *, extensions: list[BolinetteExtension] = None,
                 profile: str = None, overrides: dict[str, Any] = None):
        self._origin = origin
        self.env = core.Environment(self, profile=profile, overrides=overrides)
        self.inject = core.BolinetteInjection(self)
        self.db = DatabaseManager(self)
        self.mapper = mapping.Mapper()
        self.resources = web.BolinetteResources(self)
        super().__init__(origin, env=self.env, inject=self.inject, db=self.db,
                         mapper=self.mapper, resources=self.resources)
        self._extensions: list[BolinetteExtension] = []

        for ext in extensions or []:
            self.use_extension(ext)

        self.manifest = files.read_manifest(
            self.root_path(), params={'version': self.env.get('version', '0.0.0')}) or {}
        self.logger = core.Logger(self)
        self.validator = core.Validator(self)
        self.jwt = core.JWT(self)
        self.sockets = web.BolinetteSockets(self)

    @property
    def extensions(self) -> Iterable[BolinetteExtension]:
        return (e for e in self._extensions)

    def clear_extensions(self):
        self._extensions = []

    def use_extension(self, ext: BolinetteExtension):
        if ext not in self._extensions:
            for sub_ext in ext.dependencies:
                self.use_extension(sub_ext)
            self._extensions.append(ext)

    def has_extension(self, ext: tuple[BolinetteExtension, ...] | BolinetteExtension):
        if Extensions.ALL in self._extensions:
            return True
        if isinstance(ext, BolinetteExtension):
            return ext in self._extensions
        if isinstance(ext, tuple):
            return len(ext) > 0 and any(self.has_extension(b) for b in ext)
        raise ValueError('BolinetteContext.has_extensions only accepts BolinetteExtensions instances')
