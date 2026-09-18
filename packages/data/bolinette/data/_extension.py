from collections.abc import Sequence
from typing import override

from escondite import Cache
from muotti import mapping_protocol
from soupape import ServiceCollection, injectable

from bolinette.core import CoreExtension, startup
from bolinette.core.commands import command
from bolinette.core.events import on_stopped
from bolinette.core.extensions import Extension, NewProjectHook
from bolinette.data._databases import DatabaseManager, DatabaseSystem, database_system
from bolinette.data._mapping import SqlAlchemyProtocol
from bolinette.data._scaffold import create_data_packages, create_database_config
from bolinette.data.defaults import (
    AsyncPostgreSQL,
    AsyncSQLite,
    PostgreSQL,
    SQLite,
    create_db_tables,
    create_tables_for_memory_db,
    dispose_databases,
)
from bolinette.data.relational import AsyncTransaction, EntityManager, register_relational_services


class DataExtension(Extension):
    name = "data"
    dependencies: Sequence[type[Extension]] = (CoreExtension,)

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        injectable.singleton(DatabaseManager, cache=cache)
        injectable.singleton(EntityManager, cache=cache)
        injectable.scoped(AsyncTransaction, cache=cache)
        register_relational_services(services, cache)

        mapping_protocol(SqlAlchemyProtocol, cache=cache)

        for system in (SQLite, AsyncSQLite, PostgreSQL, AsyncPostgreSQL):
            database_system(cache=cache)(system)
        for system in cache.get(DatabaseManager.SYSTEM_CACHE_KEY, hint=type[DatabaseSystem], raises=False):
            services.add_singleton(system)

        startup(cache=cache)(create_tables_for_memory_db)
        on_stopped(cache=cache)(dispose_databases)

        command(create_db_tables, "db init", "Creates the tables in the databases", cache=cache)

    @override
    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return (create_data_packages, create_database_config)
