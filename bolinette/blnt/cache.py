from collections.abc import Callable, Awaitable
from typing import Type

from bolinette import blnt, core, web, BolinetteExtension
from bolinette.blnt.commands import Command


class BolinetteCache:
    def __init__(self):
        self.models: dict[str, Type['core.Model']] = {}
        self.mixins: dict[str, Type['core.Mixin']] = {}
        self.services: dict[str, Type['core.Service']] = {}
        self.controllers: dict[str, Type['web.Controller']] = {}
        self.middlewares: dict[str, Type['web.Middleware']] = {}
        self.topics: dict[str, Type['web.Topic']] = {}
        self.init_funcs: list[InitFunc] = []
        self.commands: dict[str, Command] = {}
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
