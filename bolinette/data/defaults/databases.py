from bolinette.data.relational import AsyncRelationalDatabase, RelationalDatabase


class SQLite:
    scheme = "sqlite://"
    python_package = "sqlalchemy"
    manager = RelationalDatabase


class AsyncSQLite:
    scheme = "sqlite+aiosqlite://"
    python_package = "aiosqlite"
    manager = AsyncRelationalDatabase


class PostgreSQL:
    scheme = "postgresql://"
    python_package = "sqlalchemy"
    manager = RelationalDatabase


class AsyncPostgreSQL:
    scheme = "postgresql+asyncpg://"
    python_package = "asyncpg"
    manager = AsyncRelationalDatabase
