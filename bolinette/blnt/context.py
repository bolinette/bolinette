from typing import Dict, Any, Tuple, List, Union

from aiohttp import web as aio_web

from bolinette import blnt, core, web, mapping, BolinetteExtension, Extensions
from bolinette.exceptions import InternalError
from bolinette.blnt.database import DatabaseManager
from bolinette.utils import paths, files
from bolinette.docs import Documentation


class BolinetteContext:
    def __init__(self, origin: str, *, extensions: List[BolinetteExtension] = None,
                 profile: str = None, overrides: Dict[str, Any] = None):
        self._ctx = {}
        self._extensions = []
        self._tables: Dict[str, Any] = {}
        self._models: Dict[str, 'core.Model'] = {}
        self._repos: Dict[str, 'core.Repository'] = {}
        self._services: Dict[str, 'core.Service'] = {}
        self._controllers: Dict[str, 'web.Controller'] = {}

        for ext in extensions or []:
            self.use_extension(ext)

        self.app = None
        self.cwd = paths.cwd()
        self.origin = origin
        self.env = blnt.Environment(self, profile=profile, overrides=overrides)
        self.manifest = files.read_manifest(
            self.root_path(), params={'version': self.env.get('version', '0.0.0')}) or {}
        self.logger = blnt.Logger(self)
        self.db = DatabaseManager(self)
        self.mapper = mapping.Mapper(self)
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

    def model(self, name) -> Any:
        return self._models[name]

    def clear_extensions(self):
        self._extensions = []

    def use_extension(self, ext: BolinetteExtension):
        if ext not in self._extensions:
            for sub_ext in ext.dependencies:
                self.use_extension(sub_ext)
            self._extensions.append(ext)

    def has_extension(self, ext: Union[Tuple[BolinetteExtension, ...], BolinetteExtension]):
        if Extensions.ALL in self._extensions:
            return True
        if isinstance(ext, BolinetteExtension):
            return ext in self._extensions
        if isinstance(ext, tuple):
            return len(ext) > 0 and any(self.has_extension(b) for b in ext)
        raise ValueError('BolinetteContext.has_extensions only accepts BolinetteExtensions instances')

    def add_model(self, name, model: 'core.Model'):
        self._models[name] = model

    def instance_path(self, *path):
        return self.root_path('instance', *path)

    def env_path(self, *path):
        return self.root_path('env', *path)

    def static_path(self, *path):
        return self.root_path('static', *path)

    def templates_path(self, *path):
        return self.root_path('templates', *path)

    def root_path(self, *path):
        return paths.join(self.cwd, *path)

    def internal_path(self, *path):
        return paths.join(self.origin, *path)

    def internal_files_path(self, *path):
        return paths.join(self.origin, '_files', *path)

    @property
    def models(self):
        return ((name, self._models[name]) for name in self._models)

    def table(self, name) -> Any:
        return self._tables[name]

    def add_table(self, name, table):
        self._tables[name] = table

    @property
    def tables(self):
        return ((name, self._tables[name]) for name in self._tables)

    def repo(self, name: str) -> Any:
        return self._repos[name]

    def add_repo(self, name, repo: 'core.Repository'):
        self._repos[name] = repo

    @property
    def repos(self):
        return ((name, self._repos[name]) for name in self._repos)

    def service(self, name) -> Any:
        if name not in self._services:
            raise InternalError(f'global.service.not_found:{name}')
        return self._services[name]

    def add_service(self, name, service: 'core.Service'):
        self._services[name] = service

    @property
    def services(self):
        return ((name, self._services[name]) for name in self._services)

    def controller(self, name) -> Any:
        return self._controllers[name]

    def add_controller(self, name, controller: 'web.Controller'):
        self._controllers[name] = controller

    @property
    def controllers(self):
        return ((name, self._controllers[name]) for name in self._controllers)
