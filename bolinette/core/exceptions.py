from collections.abc import Iterator
from typing import Any, Callable

from typing_extensions import override


class BolinetteError(Exception):
    def __init__(self, message: str) -> None:
        Exception.__init__(self, message)
        self.message = message


class InitError(BolinetteError):
    def __init__(self, message: str) -> None:
        BolinetteError.__init__(self, message)
        self.message = message

    @override
    def __str__(self) -> str:
        return self.message


class InternalError(BolinetteError):
    pass


class ParameterError:
    def __init__(self, **params: str) -> None:
        self._error_params = params

    def _format_params(self, message: str, **values: Any) -> str:
        f_strings: list[str] = []
        for param, f_string in self._error_params.items():
            if param in values and values[param]:
                f_strings.append(f_string.replace("{}", str(values[param])))
        return ", ".join(f_strings + [message])


class ErrorCollection(Exception):
    def __init__(self, errors: list[BolinetteError] | None = None) -> None:
        self._errors: list[BolinetteError] = errors or []
        Exception.__init__(self, "\n".join(e.message for e in self._errors))

    def append(self, error: BolinetteError) -> None:
        self._errors.append(error)

    def __bool__(self) -> bool:
        return any(self._errors)

    def __iter__(self) -> Iterator[BolinetteError]:
        return iter(self._errors)

    @override
    def __str__(self) -> str:
        return str(self._errors)

    @override
    def __repr__(self) -> str:
        return f'<BolinetteErrors [{",".join([repr(err) for err in self._errors])}]>'


class TypingError(BolinetteError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        cls: str | None = None,
    ) -> None:
        ParameterError.__init__(self, cls="Type {}")
        BolinetteError.__init__(self, self._format_params(message, cls=cls))


class InjectionError(BolinetteError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        cls: type[Any] | None = None,
        func: Callable[..., Any] | None = None,
        param: str | None = None,
    ) -> None:
        ParameterError.__init__(self, cls="Type {}", func="Callable {}", param="Parameter '{}'")
        BolinetteError.__init__(
            self,
            self._format_params(
                message,
                cls=cls,
                func=func.__qualname__ if func is not None else None,
                param=param,
            ),
        )


class EnvironmentError(BolinetteError):
    pass


class ExpressionError(BolinetteError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Expression error: {message}")


class MappingError(BolinetteError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        src: str | None = None,
        dest: str | None = None,
    ) -> None:
        ParameterError.__init__(self, dest="Destination path '{}'", src="From source path '{}'")
        BolinetteError.__init__(self, self._format_params(message, dest=dest, src=src))


class InitMappingError(InitError):
    pass
