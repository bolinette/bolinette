from typing import Any

from aiohttp import web as aio_web

from bolinette import abc, blnt, web, mapping, BolinetteExtension, Extensions
from bolinette.blnt.database import DatabaseManager
from bolinette.utils import paths, files
from bolinette.docs import Documentation


class BolinetteContext(abc.Context):
    def __init__(self, origin: str, *, extensions: list[BolinetteExtension] = None,
                 profile: str = None, overrides: dict[str, Any] = None):
        super().__init__(origin,
            inject=blnt.BolinetteInjection(self)
        )
        self._ctx: dict[str, Any] = {}
        self._extensions: list[BolinetteExtension] = []

        for ext in extensions or []:
            self.use_extension(ext)

        self.app: aio_web.Application | None = None
        self.cwd = paths.cwd()
        self.env = blnt.Environment(self, profile=profile, overrides=overrides)
        self.manifest = files.read_manifest(
            self.root_path(), params={'version': self.env.get('version', '0.0.0')}) or {}
        self.logger = blnt.Logger(self)
        self.db = DatabaseManager(self)
        self.mapper = mapping.Mapper()
        self.validator = blnt.Validator(self)
        self.jwt = blnt.JWT(self)
        self.resources = web.BolinetteResources(self)
        self.docs = Documentation(self)
        self.sockets = web.BolinetteSockets(self)

    def init_web(self, app: aio_web.Application):
        self.app = app
        self.resources.init_web(app)

    def init_sockets(self, app: aio_web.Application):
        self.app = app
        self.sockets.init_socket_handler()

    def __getitem__(self, key):
        return self._ctx[key]

    def __setitem__(self, key, value):
        self._ctx[key] = value

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

    def internal_path(self, *path):
        return paths.join(self._origin, *path)

    def internal_files_path(self, *path):
        return paths.join(self._origin, '_files', *path)

    def root_path(self, *path):
        return paths.join(self.cwd, *path)

    def instance_path(self, *path):
        return self.root_path('instance', *path)

    def env_path(self, *path):
        return self.root_path('env', *path)

    def static_path(self, *path):
        return self.root_path('static', *path)

    def templates_path(self, *path):
        return self.root_path('templates', *path)
