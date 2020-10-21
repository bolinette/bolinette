from typing import Dict, Any, Optional

from aiohttp import web as aio_web
from bolinette.utils import paths

from bolinette import core, blnt
from bolinette.exceptions import InternalError


class BolinetteContext:
    def __init__(self, origin: str, app: Optional[aio_web.Application], *, profile=None, overrides=None):
        self.cwd = paths.cwd()
        self.origin = origin
        if app is not None:
            self.app = app
            self.env = core.Environment(self, profile=profile, overrides=overrides)
            self.db = core.DatabaseEngine(self)
            self.jwt = core.JWT(self)
            self.resources = core.BolinetteResources(self)
            self.sockets = core.BolinetteSockets(self)
            self.mapping = core.Mapping(self)
            self.validator = core.Validator(self)
            self.response = core.Response(self)
            self._tables: Dict[str, Any] = {}
            self._models: Dict[str, 'blnt.Model'] = {}
            self._repos: Dict[str, 'blnt.Repository'] = {}
            self._services: Dict[str, 'blnt.Service'] = {}
            self._controllers: Dict[str, 'blnt.Controller'] = {}
            self._ctx = {}

    def __getitem__(self, key):
        return self._ctx[key]

    def __setitem__(self, key, value):
        self._ctx[key] = value

    def model(self, name) -> Any:
        return self._models[name]

    def add_model(self, name, model: 'blnt.Model'):
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
        return iter(self._models.items())

    def table(self, name) -> Any:
        return self._tables[name]

    def add_table(self, name, table):
        self._tables[name] = table

    @property
    def tables(self):
        return iter(self._tables.items())

    def repo(self, name) -> Any:
        return self._repos[name]

    def add_repo(self, name, repo: 'blnt.Repository'):
        self._repos[name] = repo

    @property
    def repos(self):
        return iter(self._repos.items())

    def service(self, name) -> Any:
        if name not in self._services:
            raise InternalError(f'global.service.not_found:{name}')
        return self._services[name]

    def add_service(self, name, service: 'blnt.Service'):
        self._services[name] = service

    @property
    def services(self):
        return iter(self._services.items())

    def controller(self, name) -> Any:
        return self._controllers[name]

    def add_controller(self, name, controller: 'blnt.Controller'):
        self._controllers[name] = controller

    @property
    def controllers(self):
        return iter(self._repos.items())
