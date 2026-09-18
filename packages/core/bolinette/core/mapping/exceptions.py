from typing import Any

from peritype import TWrap

from bolinette.core.exceptions import BolinetteError
from bolinette.core.expressions import ExpressionNode


class MappingError(BolinetteError):
    def __init__(
        self,
        message: str,
        *,
        dest: ExpressionNode | None = None,
        src: ExpressionNode | None = None,
    ) -> None:
        parts: list[str] = []
        if dest is not None:
            parts.append(f"Destination path '{dest}'")
        if src is not None:
            parts.append(f"From source path '{src}'")
        parts.append(message)
        BolinetteError.__init__(self, ", ".join(parts))
        self.dest = dest
        self.src = src


class SourceNotFoundError(MappingError):
    pass


class DestinationNotNullableError(MappingError):
    pass


class ConversionError(MappingError):
    def __init__(
        self,
        message: str,
        *,
        target: "TWrap[Any] | None" = None,
        dest: ExpressionNode | None = None,
        src: ExpressionNode | None = None,
    ) -> None:
        MappingError.__init__(self, message, dest=dest, src=src)
        self.target = target


class InstantiationError(MappingError):
    pass


class ImmutableFieldError(MappingError):
    pass


class NoProtocolError(MappingError):
    pass


class ValidationError(MappingError):
    def __init__(self, errors: list[MappingError]) -> None:
        MappingError.__init__(self, f"{len(errors)} mapping error(s):\n" + "\n".join(f"  - {e}" for e in errors))
        self.errors = errors


class MappingConfigurationError(BolinetteError):
    def __init__(self, problems: list[str]) -> None:
        BolinetteError.__init__(
            self, f"{len(problems)} invalid mapping(s):\n" + "\n".join(f"  - {p}" for p in problems)
        )
        self.problems = problems
