from typing import List, Callable, Dict, Type, Awaitable

from bolinette import blnt, core, web, BolinetteExtension
from bolinette.blnt.commands import Command


class BolinetteCache:
    def __init__(self):
        self.models: Dict[str, Type['core.Model']] = {}
        self.mixins: Dict[str, Type['core.Mixin']] = {}
        self.services: Dict[str, Type['core.Service']] = {}
        self.controllers: Dict[str, Type['web.Controller']] = {}
        self.middlewares: Dict[str, Type['web.Middleware']] = {}
        self.topics: Dict[str, Type['web.Topic']] = {}
        self.init_funcs: List[InitFunc] = []
        self.commands: Dict[str, Command] = {}
        self.seeders = []


cache = BolinetteCache()


class InitFunc:
    def __init__(self, func: Callable[['blnt.BolinetteContext'], Awaitable[None]], ext: BolinetteExtension):
        self._func = func
        self._ext = ext

    @property
    def extension(self):
        return self._ext

    def __call__(self, context: 'blnt.BolinetteContext'):
        return self._func(context)

    def __str__(self):
        return self._func.__name__
