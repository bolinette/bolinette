from typing import List, Callable, Dict, Type

from bolinette import blnt, core, web


class BolinetteCache:
    def __init__(self):
        self.models: Dict[str, Type['core.Model']] = {}
        self.mixins: Dict[str, Type['core.Mixin']] = {}
        self.services: Dict[str, Type['core.Service']] = {}
        self.controllers: Dict[str, Type['web.Controller']] = {}
        self.middlewares: Dict[str, Type['web.Middleware']] = {}
        self.topics: Dict[str, Type['web.Topic']] = {}
        self.init_funcs: List[Callable[['blnt.BolinetteContext'], None]] = []
        self.commands: Dict[str, Callable] = {}
        self.seeders = []


cache = BolinetteCache()
