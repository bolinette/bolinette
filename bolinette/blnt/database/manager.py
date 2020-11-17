from typing import Dict

from bolinette import blnt
from bolinette.blnt.database import RelationalDatabase, CollectionDatabase, DatabaseEngine
from bolinette.exceptions import InternalError, InitError


class DatabaseManager:
    _DBMS = {
        'sqlite://': RelationalDatabase,
        'mongodb://': CollectionDatabase
    }

    def __init__(self, context: 'blnt.BolinetteContext'):
        self.context = context
        self.engines: Dict[str, DatabaseEngine] = {}
        self._init_databases()

    def _init_databases(self):
        def _init_database(_name: str, _uri: str):
            for dbms in self._DBMS:
                if _uri.startswith(dbms):
                    self.engines[_name] = self._DBMS[dbms](_uri)
                    break
            else:
                raise InitError(f'Unsupported database system for URI "{_uri}"')
        try:
            conf = self.context.env['database']
            if isinstance(conf, str):
                _init_database('default', conf)
            elif isinstance(conf, dict):
                for name, uri in conf.items():
                    if not isinstance(uri, str):
                        raise ValueError()
                    _init_database(name, uri)
            else:
                raise ValueError()
        except ValueError:
            raise InitError('Bad database configuration in env files')

    @property
    def engine(self):
        if 'default' in self.engines:
            return self.engines['default']
        raise InternalError('internal.db.no_default_engine')

    def __getitem__(self, key):
        if key in self.engines:
            return self.engines[key]
        raise InternalError(f'internal.db.no_engine:{key}')

    def __contains__(self, key):
        return key in self.engines

    async def open_transaction(self):
        for _, engine in self.engines.items():
            await engine.open_transaction()

    async def close_transaction(self):
        for _, engine in self.engines.items():
            await engine.close_transaction()

    async def rollback_transaction(self):
        for _, engine in self.engines.items():
            await engine.rollback_transaction()

    async def create_all(self):
        for _, engine in self.engines.items():
            await engine.create_all()

    async def drop_all(self):
        for _, engine in self.engines.items():
            await engine.drop_all()

    async def run_seeders(self, context: 'blnt.BolinetteContext'):
        for func in blnt.cache.seeders:
            await func(context)
