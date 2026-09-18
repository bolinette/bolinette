# bolinette-data

The Bolinette data extension: a relational layer built on [SQLAlchemy](https://pypi.org/project/SQLAlchemy/).

It reads the databases from the application configuration, binds each declarative base to one of them, and registers a `Repository` and a `Service` for every entity it finds.
The injector scope is the unit of work, so a transaction opens when a scope first needs a session and commits when that scope closes.

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.data.relational import declarative_base


@declarative_base("default")
class Base(DeclarativeBase):
    pass


class Example(Base):
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
```

## Installation

```shell
$ pip install bolinette-data  # or use your preferred package manager
```

## Requirements

Bolinette-data requires Python 3.13 (or newer), and depends on [bolinette](https://pypi.org/project/bolinette/) and [SQLAlchemy](https://pypi.org/project/SQLAlchemy/).
The driver of a database is imported only when a connection is configured for it, so an application using SQLite never needs the PostgreSQL driver installed.

## What the data extension does

- **Connections from configuration** — the `data.databases` section lists them by name, url and echo flag.
  The url scheme picks the system: synchronous and asynchronous SQLite and PostgreSQL come bundled, and `database_system` registers another.
- **Entities without a decorator** — a declarative base is bound to a connection with `declarative_base`, and every mapped class of that base is an entity.
- **Repository** — the data access layer, with `find_all`, `get_by_primary`, `first`, `iterate`, `add`, `delete` and `flush`.
  `iterate` takes any SQLAlchemy statement, so a complex query stays a SQLAlchemy query.
- **Service** — the layer between the repository and your application, where business logic goes.
  `create` and `update` take a payload, map it onto the entity, then check that no non-nullable column was left empty.
- **Your own implementations** — a subclass decorated with `repository()` or `service()` replaces the default for that entity.
- **Unit of work** — `AsyncTransaction` is entered and exited by the injector scope, committing on success and rolling back on error.
  Sessions open lazily, one per engine.
- **Table creation** — in-memory databases are created at startup, and `blnt db init` creates the tables of every other connection.

## License

Bolinette is released under the MIT license, see [LICENSE.txt](LICENSE.txt).
