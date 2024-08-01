import logging
import logging.handlers
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, Protocol, override

from bolinette.core.injection.resolver import ArgResolverOptions
from bolinette.core.objects import CoreSection, FileLoggingConfig, StreamLoggingConfig


class SupportsWrite[T](Protocol):
    def write(self, __s: T) -> object:
        pass


class ConsoleColorCode:
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


class BasicFormatter(logging.Formatter):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    @override
    def format(self, record: logging.LogRecord) -> str:
        record.timestamp = datetime.fromtimestamp(record.created, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        record.service = self.name
        formatted_str = "%(timestamp)s [%(levelname)s] <%(service)s> %(message)s"
        return logging.Formatter(formatted_str).format(record)


class ColorFormatter(logging.Formatter):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: ConsoleColorCode.FgBlue,
        logging.INFO: ConsoleColorCode.FgGreen,
        logging.WARNING: ConsoleColorCode.FgYellow,
        logging.WARN: ConsoleColorCode.FgYellow,
        logging.ERROR: ConsoleColorCode.FgRed,
        logging.CRITICAL: ConsoleColorCode.BgRed + ConsoleColorCode.FgBlack,
        logging.FATAL: ConsoleColorCode.BgRed + ConsoleColorCode.FgBlack,
    }

    @override
    def format(self, record: logging.LogRecord) -> str:
        record.timestamp = datetime.fromtimestamp(record.created, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        record.service = self.name
        formatted_str = (
            f"%(timestamp)s "
            f"[{ConsoleColorCode.Bright}{self.COLORS[record.levelno]}%(levelname)s{ConsoleColorCode.Reset}] "
            f"<{ConsoleColorCode.FgGreen}%(service)s{ConsoleColorCode.Reset}> %(message)s"
        )
        return logging.Formatter(formatted_str).format(record)


class Logger[T](logging.Logger): ...


class LoggerArgResolver:
    def __init__(self, core_config: CoreSection) -> None:
        self.config = core_config

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.t.cls is Logger

    def resolve(self, options: ArgResolverOptions) -> logging.Logger:
        logger = logging.getLogger(f"__blnt_logger__.{options.t}")
        if not logger.hasHandlers():
            logger.setLevel(logging.DEBUG)
            logger_name = options.t.vars[0].__qualname__
            if self.config.logging is None:
                config = StreamLoggingConfig()
                config.type = "stderr"
                config.color = True
                self._add_console_logger(logger, logger_name, config)
            else:
                for config in self.config.logging:
                    if config.type == "stderr":
                        self._add_console_logger(logger, logger_name, config)
                    elif config.type == "file":
                        self._add_file_logger(logger, logger_name, config)
        return logger

    @staticmethod
    def _add_console_logger(logger: logging.Logger, name: str, config: StreamLoggingConfig) -> None:
        handler = logging.StreamHandler()
        handler.setLevel(config.level)
        if config.color:
            handler.setFormatter(ColorFormatter(name))
        else:
            handler.setFormatter(BasicFormatter(name))
        logger.addHandler(handler)

    @staticmethod
    def _add_file_logger(logger: logging.Logger, name: str, config: FileLoggingConfig) -> None:
        log_path = Path(config.path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.TimedRotatingFileHandler(log_path, when="midnight", utc=True)
        handler.setLevel(config.level)
        handler.setFormatter(BasicFormatter(name))
        logger.addHandler(handler)
