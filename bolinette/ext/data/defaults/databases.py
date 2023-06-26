from bolinette.ext.data.relational import RelationalDatabase


class SQLite:
    scheme = "sqlite+aiosqlite://"
    python_package = "aiosqlite"
    manager = RelationalDatabase
