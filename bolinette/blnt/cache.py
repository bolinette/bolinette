from collections.abc import Callable, Awaitable

from bolinette import blnt, core, web, BolinetteExtension
from bolinette.blnt.commands import Command


class BolinetteCache:
    def __init__(self):
        self.models: dict[str, type[core.Model]] = {}
        self.mixins: dict[str, type[core.Mixin]] = {}
        self.services: dict[str, type[core.Service | core.SimpleService]] = {}
        self.controllers: dict[str, type[web.Controller]] = {}
        self.middlewares: dict[str, type[web.Middleware]] = {}
        self.topics: dict[str, type[web.Topic]] = {}
        self.init_funcs: list[InitFunc] = []
        self.commands: dict[str, Command] = {}
        self.seeders = []


cache = BolinetteCache()


class InitFunc:
    def __init__(self, func: Callable[['blnt.BolinetteContext'], Awaitable[None]],
                 ext: BolinetteExtension | None):
        self._func = func
        self._ext = ext

    @property
    def extension(self):
        return self._ext

    def __call__(self, context: 'blnt.BolinetteContext'):
        return self._func(context)

    def __str__(self):
        return self._func.__name__
