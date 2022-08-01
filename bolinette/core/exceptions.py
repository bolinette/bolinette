from collections.abc import Iterator as _Iterator
from typing import Any, Callable


class BolinetteError(Exception):
    def __init__(self, message: str) -> None:
        Exception.__init__(self, message)
        self._message = message

    @property
    def message(self) -> str:
        return self._message


class ErrorCollection(Exception):
    def __init__(self, errors: list[BolinetteError] | None = None) -> None:
        self._errors: list[BolinetteError] = errors or []

    def append(self, error: BolinetteError) -> None:
        self._errors.append(error)

    def __bool__(self) -> bool:
        return any(self._errors)

    def __iter__(self) -> _Iterator[BolinetteError]:
        return iter(self._errors)

    def __str__(self) -> str:
        return str(self._errors)

    def __repr__(self) -> str:
        return f'<BolinetteErrors [{",".join([repr(err) for err in self._errors])}]>'


class InternalError(BolinetteError):
    pass


class InjectionError(InternalError):
    pass


class TypeNotRegisteredInjectionError(InjectionError):
    def __init__(self, cls: type[Any]) -> None:
        super().__init__(f"Type {cls} is not a registered type in the injection system")


class TypeRegisteredInjectionError(InjectionError):
    def __init__(self, cls: type[Any]) -> None:
        super().__init__(f"Type {cls} is already a registered type")


class InstanceExistsInjectionError(InjectionError):
    def __init__(self, cls: type[Any]) -> None:
        super().__init__(f"Type {cls} has already been instanciated in this scope")


class InstanceNotExistInjectionError(InjectionError):
    def __init__(self, cls: type[Any]) -> None:
        super().__init__(f"Type {cls} has not been instanciated in this scope")


class AnnotationMissingInjectionError(InjectionError):
    def __init__(self, func: Callable, param: str) -> None:
        super().__init__(
            f"Callable {func} Parameter '{param}' requires a type annotation"
        )


class NoPositionalParameterInjectionError(InjectionError):
    def __init__(self, func: Callable) -> None:
        super().__init__(
            f"'Callable {func}: positional only parameters and positional wildcards are not allowed"
        )


class NoLiteralMatchInjectionError(InjectionError):
    def __init__(self, func: Callable, param: str, name: str) -> None:
        super().__init__(
            f"Callable {func} Parameter '{param}': "
            f"literal '{name}' does not match any registered type"
        )


class TooManyLiteralMatchInjectionError(InjectionError):
    def __init__(self, func: Callable, param: str, name: str, count: int) -> None:
        super().__init__(
            f"Callable {func} Parameter '{param}': "
            f"literal '{name}' matches with {count} registered types, use a more explicit name"
        )


class InvalidArgCountInjectionError(InjectionError):
    def __init__(self, func: Callable, expected: int, count: int) -> None:
        super().__init__(
            f"Callable {func}: expected {expected} arguments, {count} given"
        )


class NoScopedContextInjectionError(InjectionError):
    def __init__(self, cls: type[Any]) -> None:
        super().__init__(
            f"Type {cls}: cannot instanciate a scoped service outside of a scoped session"
        )


class EnvironmentError(BolinetteError):
    pass


class InitEnvironmentError(EnvironmentError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InitError(Exception):
    def __init__(self, message: str = None, *, inner: Exception = None) -> None:
        self.message = message
        self.inner = inner

    def __str__(self) -> str:
        if self.message is None:
            return str(self.inner)
        return self.message
