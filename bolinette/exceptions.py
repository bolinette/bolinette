from collections.abc import Iterator
from typing import Any, Callable


class BolinetteError(Exception):
    def __init__(self, message: str) -> None:
        Exception.__init__(self, message)
        self.message = message


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

    def __str__(self) -> str:
        return str(self._errors)

    def __repr__(self) -> str:
        return f'<BolinetteErrors [{",".join([repr(err) for err in self._errors])}]>'


class InternalError(BolinetteError):
    pass


class InjectionError(InternalError, ParameterError):
    def __init__(
        self,
        message: str,
        *,
        cls: type[Any] | None = None,
        func: Callable | None = None,
        param: str | None = None,
    ) -> None:
        ParameterError.__init__(
            self, cls="Type {}", func="Callable {}", param="Parameter '{}'"
        )
        InternalError.__init__(
            self, self._format_params(message, cls=cls, func=func, param=param)
        )


class EnvironmentError(BolinetteError):
    pass


class InitError(Exception):
    def __init__(
        self, message: str | None = None, *, inner: Exception | None = None
    ) -> None:
        Exception.__init__(self, message)
        self.message = message
        self.inner = inner

    def __str__(self) -> str:
        if self.message is None:
            return str(self.inner)
        return self.message
