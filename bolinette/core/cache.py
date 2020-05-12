from typing import List, Callable, Dict, Type

from bolinette import core, data


class BolinetteCache:
    def __init__(self):
        self.models: Dict[str, Type['data.Model']] = {}
        self.services: Dict[str, Type['data.Service']] = {}
        self.init_funcs: List[Callable[['core.BolinetteContext'], None]] = []
        self.seeders = []


cache = BolinetteCache()
