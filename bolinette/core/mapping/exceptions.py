from collections.abc import Sequence
from typing import Any

from bolinette.core.exceptions import BolinetteError, ParameterError
from bolinette.core.expressions import ExpressionNode
from bolinette.core.types import Type


class MappingError(BolinetteError, ParameterError):
    def __init__(self, message: str, *, src: ExpressionNode | None = None, dest: ExpressionNode | None = None) -> None:
        ParameterError.__init__(self, dest="Destination path '{}'", src="From source path '{}'")
        BolinetteError.__init__(self, self._format_params(message, dest=dest, src=src))
        self.src = src
        self.dest = dest


class SourceNotFoundError(MappingError):
    src: ExpressionNode
    dest: ExpressionNode

    def __init__(self, src: ExpressionNode, dest: ExpressionNode, t: Type[Any]) -> None:
        super().__init__(
            f"Source path not found, could not bind a None value to non nullable type {t}", src=src, dest=dest
        )


class DestinationNotNullableError(MappingError):
    src: ExpressionNode
    dest: ExpressionNode

    def __init__(self, src: ExpressionNode, dest: ExpressionNode, t: Type[Any]) -> None:
        super().__init__(f"Could not bind a None value to non nullable type {t}", src=src, dest=dest)


class InstantiationError(MappingError):
    dest: ExpressionNode

    def __init__(self, dest: ExpressionNode, t: Type[Any]) -> None:
        super().__init__(
            f"Could not instantiate type {t}, make sure the __init__ has no required parameters", dest=dest
        )


class IgnoreImpossibleError(MappingError):
    dest: ExpressionNode

    def __init__(self, dest: ExpressionNode, t: Type[Any]) -> None:
        super().__init__(f"Could not ignore attribute, type {t} is not nullable", dest=dest)


class UnionNotAllowedError(MappingError):
    def __init__(self, dest: ExpressionNode, t: Type[Any]) -> None:
        super().__init__(f"Destination type {t} is a union, please use use_type(...) in profile", dest=dest)


class TypeMismatchError(MappingError):
    src: ExpressionNode
    dest: ExpressionNode

    def __init__(self, src: ExpressionNode, dest: ExpressionNode, source: Type[Any], target: Type[Any]) -> None:
        super().__init__(f"Selected type {source} is not assignable to {target}", src=src, dest=dest)


class TypeNotIterableError(MappingError):
    src: ExpressionNode
    dest: ExpressionNode

    def __init__(self, src: ExpressionNode, dest: ExpressionNode, source: Type[Any], target: Type[Any]) -> None:
        super().__init__(f"Could not map non iterable type {source} to {target}", src=src, dest=dest)


class ImmutableCollectionError(MappingError):
    dest: ExpressionNode

    def __init__(self, dest: ExpressionNode) -> None:
        super().__init__("Could not use an existing tuple instance, tuples are immutable", dest=dest)


class ConvertionError(MappingError):
    src: ExpressionNode
    dest: ExpressionNode

    def __init__(self, src: ExpressionNode, dest: ExpressionNode, value: Any, target: Type[Any]) -> None:
        super().__init__(f"Could not convert value '{value}' to {target}", src=src, dest=dest)
        self.target = target


class ValidationError(MappingError):
    def __init__(self, errors: Sequence[MappingError]) -> None:
        super().__init__("Mapping errors raised during validation")
        self.errors = errors
