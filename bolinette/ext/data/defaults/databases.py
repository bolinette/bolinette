from bolinette.ext.data.manager import database_system
from bolinette.ext.data.database import RelationalDatabase


@database_system()
class SQLite:
    scheme = "sqlite+aiosqlite://"
    python_package = "aiosqlite"
    manager = RelationalDatabase
