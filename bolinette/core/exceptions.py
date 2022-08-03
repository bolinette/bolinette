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
    def __init__(
        self,
        message: str,
        *,
        cls: str | None = None,
        func: Callable | None = None,
        param: str | None = None,
    ) -> None:
        strs = [message]
        if param is not None:
            strs.insert(0, f"Parameter '{param}'")
        if func is not None:
            strs.insert(0, f"Callable {func}")
        if cls is not None:
            strs.insert(0, f"Type {cls}")
        super().__init__(', '.join(strs))


class EnvironmentError(BolinetteError):
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
