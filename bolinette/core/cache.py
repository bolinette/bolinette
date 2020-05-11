from typing import List, Callable

from bolinette import core


class BolinetteCache:
    def __init__(self):
        self.models = {}
        self.init_funcs: List[Callable[[core.BolinetteContext], None]] = []
        self.seeders = []


cache = BolinetteCache()
