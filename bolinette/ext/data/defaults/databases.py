from bolinette.ext.data import __data_cache__, database_system
from bolinette.ext.data.relational import RelationalDatabase


@database_system(cache=__data_cache__)
class SQLite:
    scheme = "sqlite+aiosqlite://"
    python_package = "aiosqlite"
    manager = RelationalDatabase
