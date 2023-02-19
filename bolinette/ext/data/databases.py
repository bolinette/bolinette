import importlib
import re
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from bolinette import Cache, Injection, init_method, injectable
from bolinette.ext.data import DataSection, __data_cache__
from bolinette.ext.data.exceptions import DatabaseError


@injectable(cache=__data_cache__, strategy="singleton")
class DatabaseManager:
    DBMS_RE = re.compile(r"^([^:]*://).*$")

    def __init__(
        self,
        cache: Cache,
        section: DataSection,
        inject: Injection,
    ) -> None:
        self._cache = cache
        self._section = section
        self._inject = inject
        self._systems: list[DatabaseSystem] = []
        self._connections: list[_DatabaseConnection] = []

    def has_system(self, scheme: str) -> bool:
        return any(s for s in self._systems if s.scheme == scheme)

    def get_system(self, scheme: str) -> "DatabaseSystem":
        return next(s for s in self._systems if s.scheme == scheme)

    def has_connection(self, name: str) -> bool:
        return any(s for s in self._connections if s.name == name)

    def get_connection(self, name: str) -> "_DatabaseConnection":
        return next(s for s in self._connections if s.name == name)

    @init_method
    def _init_systems(self) -> None:
        systems = [t() for t in self._cache.get(DatabaseSystem, hint=type[DatabaseSystem], raises=False)]
        if not systems:
            raise DatabaseError(f"No system was registered with @{database_system.__name__}")
        for system in systems:
            try:
                importlib.import_module(system.python_package)
            except ModuleNotFoundError:
                raise DatabaseError(
                    f"Python package '{system.python_package}' was not found",
                    system=system.scheme,
                )
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
            self._connections.append(_DatabaseConnection(db_config.name, db_config.url, db_config.echo, system.manager))


class DatabaseSystem(Protocol):
    scheme: str
    python_package: str
    manager: type[Any]

    def __init__(self) -> None:
        pass


SystemT = TypeVar("SystemT", bound=DatabaseSystem)


def database_system(*, cache: Cache | None = None) -> Callable[[type[SystemT]], type[SystemT]]:
    def decorator(cls: type[SystemT]) -> type[SystemT]:
        (cache or __data_cache__).add(DatabaseSystem, cls)
        return cls

    return decorator


class _DatabaseConnection:
    def __init__(self, name: str, url: str, echo: bool, manager: Any) -> None:
        self.name = name
        self.url = url
        self.echo = echo
        self.manager = manager