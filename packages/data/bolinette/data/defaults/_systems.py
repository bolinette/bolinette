from bolinette.data.relational import AsyncRelationalDatabase, RelationalDatabase, RelationalSystem


class SQLite(RelationalSystem):
    scheme = "sqlite://"
    python_package = "sqlalchemy"
    database = RelationalDatabase


class AsyncSQLite(RelationalSystem):
    scheme = "sqlite+aiosqlite://"
    python_package = "aiosqlite"
    database = AsyncRelationalDatabase


class PostgreSQL(RelationalSystem):
    scheme = "postgresql://"
    python_package = "sqlalchemy"
    database = RelationalDatabase


class AsyncPostgreSQL(RelationalSystem):
    scheme = "postgresql+asyncpg://"
    python_package = "asyncpg"
    database = AsyncRelationalDatabase
