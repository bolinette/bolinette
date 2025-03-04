from bolinette import core
from bolinette.core import Cache, startup
from bolinette.core.command import command
from bolinette.core.environment import environment
from bolinette.core.extension import Extension, ExtensionModule
from bolinette.core.injection import injectable, injection_arg_resolver
from bolinette.core.mapping import mapping_worker
from bolinette.data import DatabaseManager, DataSection, database_system
from bolinette.data.defaults import (
    AsyncPostgreSQL,
    AsyncSessionArgResolver,
    AsyncSQLite,
    OrmColumnTypeMapper,
    PostgreSQL,
    SQLite,
    create_db_tables,
)
from bolinette.data.relational import AsyncTransaction, EntityManager
from bolinette.data.relational.manager import create_tables_for_memory_db


class DataExtension:
    def __init__(self, cache: Cache) -> None:
        self.name = "data"
        self.dependencies: list[ExtensionModule[Extension]] = [core]

        environment("data", cache=cache)(DataSection)

        injectable(strategy="singleton", cache=cache)(DatabaseManager)
        injectable(strategy="singleton", cache=cache)(EntityManager)
        injectable(strategy="scoped", cache=cache)(AsyncTransaction)
        injection_arg_resolver(scoped=True, cache=cache)(AsyncSessionArgResolver)

        mapping_worker(match_all=True)(OrmColumnTypeMapper)

        database_system(cache=cache)(SQLite)
        database_system(cache=cache)(AsyncSQLite)
        database_system(cache=cache)(PostgreSQL)
        database_system(cache=cache)(AsyncPostgreSQL)

        startup(cache=cache)(create_tables_for_memory_db)

        command(
            "db init",
            summary="Creates the tables in database",
            cache=cache,
            run_startup=True,
        )(create_db_tables)
