from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from bolinette.core.mapping._absence import MapMode, Maybe, is_present
from bolinette.core.mapping._spec import FieldOverride, FieldSpec
from bolinette.core.mapping.exceptions import DestinationNotNullableError, MappingError, SourceNotFoundError


class Action(Enum):
    ASSIGN = auto()
    SKIP = auto()
    FAIL = auto()


@dataclass(frozen=True, slots=True)
class Decision:
    action: Action
    value: Any = None
    error: type[MappingError] = MappingError
    reason: str = ""


def decide(presence: Maybe[Any], spec: FieldSpec, mode: MapMode, override: FieldOverride) -> Decision:
    if override.ignore:
        return Decision(Action.SKIP)

    writable = spec.writable or override.allow_write
    if override.read_only:
        writable = False

    if not writable:
        return Decision(Action.SKIP)

    if is_present(presence):
        if presence is None and not spec.nullable:
            return Decision(
                Action.FAIL,
                error=DestinationNotNullableError,
                reason="cannot bind a None value to a non-nullable field",
            )
        return Decision(Action.ASSIGN, value=presence)

    if mode is MapMode.MERGE:
        return Decision(Action.SKIP)

    if override.default_factory is not None:
        return Decision(Action.ASSIGN, value=override.default_factory())

    if spec.self_populating:
        return Decision(Action.SKIP)

    if spec.nullable:
        return Decision(Action.ASSIGN, value=None)

    return Decision(
        Action.FAIL,
        error=SourceNotFoundError,
        reason="source path not found and destination has no default",
    )
