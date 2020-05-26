from typing import Dict, Any

from aiohttp import web as aio_web

from bolinette import core, env, blnt


class BolinetteContext:
    def __init__(self, app: aio_web.Application):
        self.app = app
        self.env = env
        self.db = core.DatabaseEngine(self)
        self.jwt = core.JWT()
        self.resources = core.BolinetteResources(self)
        self.sockets = core.BolinetteSockets(self)
        self.mapping = core.Mapping(self)
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
