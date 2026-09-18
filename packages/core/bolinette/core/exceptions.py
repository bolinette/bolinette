from typing import Any, override


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
            if values.get(param):
                f_strings.append(f_string.replace("{}", str(values[param])))
        return ", ".join([*f_strings, message])


class InitError(BolinetteError):
    def __init__(self, message: str) -> None:
        BolinetteError.__init__(self, message)
        self.message = message

    @override
    def __str__(self) -> str:
        return self.message


class ConfigurationError(BolinetteError):
    pass
