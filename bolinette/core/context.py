from typing import Any
from collections.abc import Iterable

from bolinette import abc, core, web, mapping
from bolinette.core.database import DatabaseManager
from bolinette.utils import files


class BolinetteContext(abc.Context):
    def __init__(self, origin: str, *, profile: str = None, overrides: dict[str, Any] = None):
        self._origin = origin
        self.env = core.Environment(self, profile=profile, overrides=overrides)
        self.inject = core.BolinetteInjection(self)
        self.db = DatabaseManager(self)
        self.mapper = mapping.Mapper()
        self.resources = web.BolinetteResources(self)
        super().__init__(origin, env=self.env, inject=self.inject, db=self.db,
                         mapper=self.mapper, resources=self.resources)

        self.manifest = files.read_manifest(
            self.root_path(), params={'version': self.env.get('version', '0.0.0')}) or {}
        self.logger = core.Logger(self)
        self.validator = core.Validator(self)
        self.jwt = core.JWT(self)
        self.sockets = web.BolinetteSockets(self)
