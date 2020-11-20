from typing import Dict, Any, Optional

from aiohttp import web as aio_web
from bolinette.utils import paths

from bolinette import blnt, core, web, mapping
from bolinette.exceptions import InternalError


class BolinetteContext:
    def __init__(self, origin: str, app: Optional[aio_web.Application], *, profile=None, overrides=None):
        self._ctx = {}
        self.cwd = paths.cwd()
        self.origin = origin
        self.logger = blnt.Logger()
        if app is not None:
            self.app = app
            self.env = blnt.Environment(self, profile=profile, overrides=overrides)
            self.db = blnt.database.DatabaseManager(self)
            self.jwt = blnt.JWT(self)
            self.resources = web.BolinetteResources(self)
            self.sockets = web.BolinetteSockets(self)
            self.mapper = mapping.Mapper(self)
            self.validator = blnt.Validator(self)
            self.response = web.Response(self)
            self._tables: Dict[str, Any] = {}
            self._models: Dict[str, 'core.Model'] = {}
            self._repos: Dict[str, 'core.Repository'] = {}
            self._services: Dict[str, 'core.Service'] = {}
            self._controllers: Dict[str, 'web.Controller'] = {}

    def __getitem__(self, key):
        return self._ctx[key]

    def __setitem__(self, key, value):
        self._ctx[key] = value

    def model(self, name) -> Any:
        return self._models[name]

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

    def repo(self, name: str) -> 'core.Repository':
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
