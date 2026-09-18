from typing import Any

from bolinette.core.exceptions import BolinetteError, ParameterError


class ApiError(BolinetteError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        controller: type[Any] | None = None,
        route: str | None = None,
        entity: type[Any] | None = None,
    ) -> None:
        ParameterError.__init__(self, controller="Controller {}", route="Route '{}'", entity="Entity {}")
        BolinetteError.__init__(
            self,
            self._format_params(message, controller=controller, route=route, entity=entity),
        )
