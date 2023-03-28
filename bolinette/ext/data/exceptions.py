from typing import Any

from bolinette.exceptions import BolinetteError, InitError, ParameterError


class DataError(BolinetteError):
    pass


class EntityError(DataError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        entity: type[Any] | None = None,
        attribute: str | None = None,
        constraint: str | None = None,
    ) -> None:
        ParameterError.__init__(
            self,
            entity="Entity {}",
            attribute="Attribute '{}'",
            constraint="Constraint {}",
        )
        BolinetteError.__init__(
            self,
            self._format_params(message, entity=entity, attribute=attribute, constraint=constraint),
        )


class DatabaseError(DataError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        system: str | None = None,
        connection: str | None = None,
        entity: type[Any] | None = None,
    ) -> None:
        ParameterError.__init__(
            self,
            system="Database system '{}'",
            connection="Database connection '{}'",
            entity="Entity {}",
        )
        BolinetteError.__init__(
            self,
            self._format_params(message, system=system, connection=connection, entity=entity),
        )


class EntityNotFoundError(BolinetteError):
    def __init__(self, entity: type[Any]) -> None:
        super().__init__(f"Entity {entity} not found")
        self.entity = entity


class MappingInitError(InitError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Mapper Initialization: {message}")
