from bolinette.exceptions import BolinetteError, ParameterError
from bolinette.ext.data.entity import Entity


class DataError(BolinetteError):
    pass


class EntityError(DataError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        entity: type[Entity] | None = None,
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
        entity: type[Entity] | None = None,
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
