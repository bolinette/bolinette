from typing import Dict, Any

from aiohttp import web as aio_web

from bolinette import core, env, data


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
        self._models: Dict[str, 'data.Model'] = {}
        self._repos: Dict[str, 'data.Repository'] = {}
        self._services: Dict[str, 'data.Service'] = {}
        self._controllers: Dict[str, 'data.Controller'] = {}

    def model(self, name) -> Any:
        return self._models[name]

    def add_model(self, name, model: 'data.Model'):
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

    def add_repo(self, name, repo: 'data.Repository'):
        self._repos[name] = repo

    @property
    def repos(self):
        return iter(self._repos.items())

    def service(self, name) -> Any:
        return self._services[name]

    def add_service(self, name, service: 'data.Service'):
        self._services[name] = service

    @property
    def services(self):
        return iter(self._services.items())

    def controller(self, name) -> Any:
        return self._controllers[name]

    def add_controller(self, name, controller: 'data.Controller'):
        self._controllers[name] = controller

    @property
    def controllers(self):
        return iter(self._repos.items())
