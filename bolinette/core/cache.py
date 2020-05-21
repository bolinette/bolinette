from typing import List, Callable, Dict, Type

from bolinette import core, data


class BolinetteCache:
    def __init__(self):
        self.models: Dict[str, Type['data.Model']] = {}
        self.mixins: Dict[str, Type['data.Mixin']] = {}
        self.services: Dict[str, Type['data.Service']] = {}
        self.controllers: Dict[str, Type['data.Controller']] = {}
        self.topics: Dict[str, Type['data.Topic']] = {}
        self.init_funcs: List[Callable[['core.BolinetteContext'], None]] = []
        self.seeders = []


cache = BolinetteCache()
