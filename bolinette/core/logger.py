import sys
from datetime import datetime
from enum import StrEnum, unique
from typing import Protocol, TypeVar

from bolinette.core import Cache

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
    def __init__(self, cache: Cache | None = None) -> None:
        self._cache = cache or Cache()

    def _log(
        self,
        prefix: str,
        package: str | None,
        text: str,
        color: ConsoleColorCode | None = None,
        file: SupportsWrite[str] | None = None,
    ):
        strs: list[str] = []
        strs.append(f"{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')}")
        strs.append(
            f"{ConsoleColorCode.Bright}{color}{prefix.ljust(5)}{ConsoleColorCode.Reset}"
        )
        if package is None:
            package = "Application"
        strs.append(
            f"[{ConsoleColorCode.FgGreen}{package.ljust(12)[:12]}{ConsoleColorCode.Reset}]"
        )
        strs.append(text)
        print(*strs, file=file)

    def warning(self, *values, package: str | None = None, sep: str | None = None):
        self._log(
            "WARN", package, (sep or " ").join(values), color=ConsoleColorCode.FgYellow
        )

    def info(self, *values, package: str | None = None, sep: str | None = None):
        self._log(
            "INFO", package, (sep or " ").join(values), color=ConsoleColorCode.FgGreen
        )

    def debug(self, *values, package: str | None = None, sep: str | None = None):
        if self._cache.debug:
            self._log(
                "DEBUG",
                package,
                (sep or " ").join(values),
                color=ConsoleColorCode.FgBlue,
            )

    def error(self, *values, package: str | None = None, sep: str | None = None):
        self._log(
            "ERROR",
            package,
            (sep or " ").join(values),
            color=ConsoleColorCode.FgRed,
            file=sys.stderr,
        )
