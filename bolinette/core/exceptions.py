from typing import Any, override


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
        return ", ".join([*f_strings, message])


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
        func: Any | None = None,
        param: str | None = None,
    ) -> None:
        ParameterError.__init__(self, cls="Type {}", func="Callable {}", param="Parameter '{}'")
        BolinetteError.__init__(self, self._format_params(message, cls=cls, func=func, param=param))


class EnvironmentError(BolinetteError):
    pass


class InitMappingError(InitError):
    pass
