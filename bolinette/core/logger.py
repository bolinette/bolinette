from datetime import datetime
from enum import unique, StrEnum
import sys
from typing import Protocol, TypeVar

_T = TypeVar("_T", contravariant=True)


class SupportsWrite(Protocol[_T]):
    def write(self, __s: _T) -> object:
        ...


@unique
class ConsoleColorCode(StrEnum):
    Reset = "\x1b[0m"
    Bright = "\x1b[1m"
    Dim = "\x1b[2m"
    Underscore = "\x1b[4m"
    Blink = "\x1b[5m"
    Reverse = "\x1b[7m"
    Hidden = "\x1b[8m"

    FgBlack = "\x1b[30m"
    FgRed = "\x1b[31m"
    FgGreen = "\x1b[32m"
    FgYellow = "\x1b[33m"
    FgBlue = "\x1b[34m"
    FgMagenta = "\x1b[35m"
    FgCyan = "\x1b[36m"
    FgWhite = "\x1b[37m"

    BgBlack = "\x1b[40m"
    BgRed = "\x1b[41m"
    BgGreen = "\x1b[42m"
    BgYellow = "\x1b[43m"
    BgBlue = "\x1b[44m"
    BgMagenta = "\x1b[45m"
    BgCyan = "\x1b[46m"
    BgWhite = "\x1b[47m"


class Logger:
    def __init__(self, *, debug=False) -> None:
        self._debug = debug

    @property
    def is_debug(self):
        return self._debug

    @is_debug.setter
    def is_debug(self, value: bool):
        self._debug = value

    def print(
        self,
        *values,
        sep: str | None = None,
        end: str | None = None,
        file: SupportsWrite[str] | None = None,
    ):
        print(*values, sep=sep, end=end, file=file)

    def _log(
        self,
        prefix: str,
        package: str | None,
        text: str,
        fg: ConsoleColorCode | None = None,
        bg: ConsoleColorCode | None = None,
        file: SupportsWrite[str] | None = None,
    ):
        strs = [
            f"{fg or ''}{bg or ''} {prefix}{' ' if bg is not None else ''}{ConsoleColorCode.Reset}"
        ]
        if package is None:
            package = "Application"
        strs.append(f"[{ConsoleColorCode.FgGreen}{package}{ConsoleColorCode.Reset}]")
        strs.append(
            f"{ConsoleColorCode.Bright}{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')}{ConsoleColorCode.Reset}"
        )
        strs.append(text)
        print(*strs, file=file)

    def warning(self, *values, package: str | None = None, sep: str | None = None):
        self._log(
            "WARN", package, (sep or " ").join(values), bg=ConsoleColorCode.BgYellow
        )

    def info(self, *values, package: str | None = None, sep: str | None = None):
        self._log(
            "INFO", package, (sep or " ").join(values), fg=ConsoleColorCode.FgGreen
        )

    def debug(self, *values, package: str | None = None, sep: str | None = None):
        self._log(
            "DEBUG", package, (sep or " ").join(values), fg=ConsoleColorCode.FgBlue
        )

    def error(self, *values, package: str | None = None, sep: str | None = None):
        self._log(
            "ERROR",
            package,
            (sep or " ").join(values),
            bg=ConsoleColorCode.BgRed,
            file=sys.stderr,
        )
