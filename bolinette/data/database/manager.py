import traceback

from bolinette import data, Console
from bolinette.core import abc, BolinetteContext
from bolinette.data.database.engines import (
    AbstractEngine,
    RelationalDatabase,
    CollectionDatabase,
)
from bolinette.exceptions import InternalError, InitError, APIError, APIErrors


class DatabaseManager(abc.WithContext):
    _DBMS: dict[str, type[RelationalDatabase | CollectionDatabase]] = {
        "sqlite://": RelationalDatabase,
        "postgresql://": RelationalDatabase,
        "mongodb://": CollectionDatabase,
        "mongodb+srv://": CollectionDatabase,
    }

    def __init__(self, context: BolinetteContext, data_ctx: "data.DataContext"):
        super().__init__(context)
        self._data_ctx = data_ctx
        self.engines: dict[str, AbstractEngine] = {}
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
            env_key_prefix = "database."
            conf = self.context.env.get_all(startswith=env_key_prefix)
            if len(conf) <= 0:
                raise ValueError()
            for db_name, ctn_str in conf.items():
                if not isinstance(ctn_str, str):
                    raise ValueError()
                db_name = db_name[len(env_key_prefix) :] or "default"
                _init_database(db_name, ctn_str)
        except ValueError:
            raise InitError("Bad database configuration in env files")

    @property
    def engine(self):
        if "default" in self.engines:
            return self.engines["default"]
        raise InternalError("internal.db.no_default_engine")

    def get_engine(self, name: str) -> AbstractEngine:
        if name not in self.engines:
            raise AttributeError(f"No {name} database engine is defined")
        return self.engines[name]

    def __getitem__(self, key):
        if key in self.engines:
            return self.engines[key]
        raise InternalError(f"internal.db.no_engine:{key}")

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

    async def run_seeders(self, *, log: bool = False, tab: int = 0):
        try:
            for seeder in self._data_ctx.ext.cache.get_instances(data.Seeder):
                if log:
                    self.context.logger.info(f'{" " * tab}- Running {seeder.name}')
                await seeder.run(self.context, self._data_ctx)
        except (APIError, APIErrors) as e:
            traceback.print_exc()
            if log:
                self.context.logger.info(f"Seeder {seeder.name} raised errors")
            console = Console()
            if isinstance(e, APIError):
                console.error(e.message)
            elif isinstance(e, APIErrors):
                for error in e.errors:
                    console.error(error.message)
