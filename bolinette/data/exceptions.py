from typing import Any

from bolinette.core.exceptions import BolinetteError, ParameterError
from bolinette.data.model import Model


class DataError(BolinetteError):
    pass


class ModelError(DataError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        model: type[Model] | None = None,
        entity: type[Any] | None = None,
        attribute: str | None = None,
    ) -> None:
        ParameterError.__init__(
            self, model="Model {}", entity="Entity {}", attribute="Attribute '{}'"
        )
        BolinetteError.__init__(
            self,
            self._format_params(
                message, model=model, entity=entity, attribute=attribute
            ),
        )


class EntityError(DataError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        entity: type[Model] | None = None,
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
            self._format_params(
                message, entity=entity, attribute=attribute, constraint=constraint
            ),
        )
