from bolinette.core import Logger
from bolinette.data._databases import DatabaseManager


async def create_db_tables(databases: DatabaseManager) -> None:
    await databases.create_all()


async def create_tables_for_memory_db(databases: DatabaseManager, logger: Logger[DatabaseManager]) -> None:
    for database in databases.databases:
        if database.in_memory:
            logger.info("Creating tables for in-memory connection '%s'", database.name)
            await database.create_all()


async def dispose_databases(databases: DatabaseManager) -> None:
    await databases.dispose()
