from typing import Any

from bolinette.core.exceptions import BolinetteError
from bolinette.data.model import Model


class DataError(BolinetteError):
    pass


class ModelError(DataError):
    def __init__(
        self,
        message: str,
        *,
        model: type[Model] | None = None,
        entity: type[Any] | None = None,
        attribute: str | None = None,
    ) -> None:
        strs = [message]
        if attribute is not None:
            strs.insert(0, f"Attribute '{attribute}'")
        if entity is not None:
            strs.insert(0, f"Entity {entity}")
        if model is not None:
            strs.insert(0, f"Model {model}")
        super().__init__(", ".join(strs))
