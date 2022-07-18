from collections.abc import Iterator as _Iterator


class BolinetteError(Exception):
    def __init__(self, message: str, params: list[str] = None) -> None:
        Exception.__init__(self, type(self).__name__)
        self._message = message
        self._params = params or []

    def __str__(self) -> str:
        return ":".join([self._message] + self._params)

    def __repr__(self) -> str:
        return f"<BolinetteError [{type(self).__name__}] {str(self)}>"

    def __getitem__(self, index: int) -> str:
        return self._params[index]

    def __setitem__(self, index: int, value: str) -> None:
        self._params = self._params[: index - 1] + [value] + self._params[index + 1 :]

    @property
    def message(self) -> str:
        return self._message


class ErrorCollection(Exception):
    def __init__(self) -> None:
        self.errors: list[BolinetteError] = []

    def append(self, error: BolinetteError) -> None:
        self.errors.append(error)

    def __bool__(self) -> bool:
        return len(self.errors) > 0

    def __iter__(self) -> _Iterator[BolinetteError]:
        return iter(self.errors)

    def __str__(self) -> str:
        return str(self.errors)

    def __repr__(self) -> str:
        return f'<BolinetteErrors [{",".join([repr(err) for err in self.errors])}]>'


class InternalError(BolinetteError):
    pass


class InjectionError(InternalError):
    pass


class InitError(Exception):
    def __init__(self, message: str = None, *, inner: Exception = None) -> None:
        self.message = message
        self.inner = inner

    def __str__(self) -> str:
        if self.message is None:
            return str(self.inner)
        return self.message
