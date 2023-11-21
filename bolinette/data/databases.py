import importlib
import re
from collections.abc import Callable
from typing import Any, Protocol

from bolinette.core import Cache, Logger, __user_cache__
from bolinette.core.injection import Injection, init_method
from bolinette.data import DataSection
from bolinette.data.exceptions import DatabaseError


class DatabaseManager:
    DBMS_RE = re.compile(r"^([^:]*://).*$")

    def __init__(
        self,
        cache: Cache,
        section: DataSection,
        inject: Injection,
        logger: "Logger[DatabaseManager]",
    ) -> None:
        self._cache = cache
        self._section = section
        self._inject = inject
        self._systems: list[DatabaseSystem] = []
        self._connections: list[DatabaseConnection] = []
        self._logger = logger

    def has_system(self, scheme: str) -> bool:
        return any(s for s in self._systems if s.scheme == scheme)

    def get_system(self, scheme: str) -> "DatabaseSystem":
        return next(s for s in self._systems if s.scheme == scheme)

    def has_connection(self, name: str) -> bool:
        return any(s for s in self._connections if s.name == name)

    def get_connection(self, name: str) -> "DatabaseConnection":
        return next(s for s in self._connections if s.name == name)

    @init_method
    def _init_systems(self) -> None:
        systems = [t() for t in self._cache.get(DatabaseSystem, hint=type[DatabaseSystem], raises=False)]
        if not systems:
            raise DatabaseError(f"No system was registered with @{database_system.__name__}")
        for system in systems:
            try:
                importlib.import_module(system.python_package)
            except ModuleNotFoundError as e:
                raise DatabaseError(
                    f"Python package '{system.python_package}' was not found",
                    system=system.scheme,
                ) from e
            self._systems.append(system)

    @init_method
    def _init_connections(self, section: DataSection) -> None:
        for db_config in section.databases:
            re_match = self.DBMS_RE.match(db_config.url)
            if re_match is None:
                raise DatabaseError(f"Invalid URL '{db_config.url}'", connection=db_config.name)
            scheme = re_match.group(1)
            if not self.has_system(scheme):
                raise DatabaseError(
                    f"Database system supporting scheme '{scheme}' was not found", connection=db_config.name
                )
            system = self.get_system(scheme)
            self._connections.append(DatabaseConnection(db_config.name, db_config.url, db_config.echo, system.manager))
            self._logger.debug(f"Opening connection to {db_config.url}")


class DatabaseSystem(Protocol):
    scheme: str
    python_package: str
    manager: type[Any]

    def __init__(self) -> None:
        pass


def database_system[SystemT: DatabaseSystem](*, cache: Cache | None = None) -> Callable[[type[SystemT]], type[SystemT]]:
    def decorator(cls: type[SystemT]) -> type[SystemT]:
        (cache or __user_cache__).add(DatabaseSystem, cls)
        return cls

    return decorator


class DatabaseConnection:
    def __init__(self, name: str, url: str, echo: bool, manager: Any) -> None:
        self.name = name
        self.url = url
        self.echo = echo
        self.manager = manager
