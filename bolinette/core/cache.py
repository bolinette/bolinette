from collections.abc import Callable, Awaitable

from bolinette import core, data, web, BolinetteExtension
from bolinette.core.commands import Command


class BolinetteCache:
    def __init__(self):
        self.models: dict[str, type[data.Model]] = {}
        self.mixins: dict[str, type[data.Mixin]] = {}
        self.services: dict[str, type[data.Service | data.SimpleService]] = {}
        self.controllers: dict[str, type[web.Controller]] = {}
        self.middlewares: dict[str, type[web.Middleware]] = {}
        self.topics: dict[str, type[web.Topic]] = {}
        self.init_funcs: list[InitFunc] = []
        self.commands: dict[str, Command] = {}
        self.seeders = []


cache = BolinetteCache()


class InitFunc:
    def __init__(self, func: Callable[['core.BolinetteContext'], Awaitable[None]],
                 ext: BolinetteExtension | None, rerun_for_tests: bool):
        self._func = func
        self._ext = ext
        self._rerun_for_tests = rerun_for_tests

    @property
    def extension(self):
        return self._ext

    @property
    def rerun_for_tests(self):
        return self._rerun_for_tests

    def __call__(self, context: 'core.BolinetteContext'):
        return self._func(context)

    def __str__(self):
        return self._func.__name__
