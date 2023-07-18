from typing import Any

from bolinette.core.exceptions import BolinetteError, ParameterError


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


class EntityNotFoundError(DataError):
    def __init__(self, entity: type[Any]) -> None:
        super().__init__(f"Entity {entity} not found")
        self.entity = entity


class EntityValidationError(DataError):
    pass


class ColumnNotNullableError(EntityValidationError):
    def __init__(self, entity: type[Any], column: str) -> None:
        super().__init__(f"Column '{column}' of entity {entity} must not contain a null value")


class WrongColumnTypeError(EntityValidationError):
    def __init__(self, entity: type[Any], column: str, value: Any, expected: type[Any]) -> None:
        super().__init__(f"Column '{column}' of entity {entity} must be of type {expected}, got value '{value}'")
