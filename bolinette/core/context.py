from typing import Dict, Any

from bolinette import core, env, data


class BolinetteContext:
    def __init__(self):
        self.env = env
        self.models: Dict[str, 'data.Model'] = {}
        self.tables: Dict[str, Any] = {}
        self.repos: Dict[str, 'data.Repository'] = {}
        self.db = core.DatabaseEngine(self)
