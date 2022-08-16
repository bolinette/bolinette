import re
from datetime import datetime
from typing import Any

from pytest import CaptureFixture

from bolinette.core import Cache, GenericMeta, Logger, meta

output_regex = re.compile(
    r"^([\d\-T\:\.]+) "  # timestamp
    r"(?:\x1b\[\d+m)+([A-Z]+) *(?:\x1b\[\d+m)+ "  # prefix
    r"+\[(?:\x1b\[\d+m)+([^ \]]+) *(?:\x1b\[\d+m)+\] "  # package
    r"(.*)"  # message
)


class _Output:
    def __init__(self, timestamp: str, prefix: str, package: str, message: str) -> None:
        self.prefix = prefix
        self.package = package
        self.timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        self.message = message


def _parse_output(out: str) -> _Output:
    match = output_regex.match(out)
    assert match
    return _Output(match.group(1), match.group(2), match.group(3), match.group(4))


def test_logger(capsys: CaptureFixture) -> None:
    logger: Logger[Any] = Logger(Cache(debug=True))

    d1 = datetime.utcnow()

    logger.info("Test info message")
    logger.error("Test error message")
    logger.warning("Test warning message")
    logger.debug("Test debug message")

    d2 = datetime.utcnow()

    captured = capsys.readouterr()
    lines = filter(lambda s: s, [*captured.out.split("\n"), *captured.err.split("\n")])
    outputs = list(map(lambda s: _parse_output(s), lines))

    assert outputs[0].prefix == "INFO"
    assert outputs[1].prefix == "WARN"
    assert outputs[2].prefix == "DEBUG"
    assert outputs[3].prefix == "ERROR"

    assert outputs[0].package == "<Logger>"
    assert outputs[1].package == "<Logger>"
    assert outputs[2].package == "<Logger>"
    assert outputs[3].package == "<Logger>"

    assert d1 <= outputs[0].timestamp <= d2
    assert d1 <= outputs[1].timestamp <= d2
    assert d1 <= outputs[2].timestamp <= d2
    assert d1 <= outputs[3].timestamp <= d2

    assert outputs[0].message == "Test info message"
    assert outputs[1].message == "Test warning message"
    assert outputs[2].message == "Test debug message"
    assert outputs[3].message == "Test error message"


def test_logger_generic(capsys: CaptureFixture) -> None:
    class _TestClass:
        pass

    logger: Logger[Any] = Logger(Cache(debug=True))
    meta.set(logger, GenericMeta([_TestClass]))
    logger._init()

    d1 = datetime.utcnow()

    logger.info("Test info message")

    d2 = datetime.utcnow()

    captured = capsys.readouterr()
    lines = filter(lambda s: s, [*captured.out.split("\n"), *captured.err.split("\n")])
    outputs = list(map(lambda s: _parse_output(s), lines))

    assert outputs[0].prefix == "INFO"
    assert outputs[0].package == "_TestClass"
    assert d1 <= outputs[0].timestamp <= d2
    assert outputs[0].message == "Test info message"


def test_logger_debug(capsys: CaptureFixture) -> None:
    cache = Cache()

    logger: Logger[Any] = Logger(cache)

    logger.debug("Test 1")
    captured = capsys.readouterr()

    assert captured.out == ""

    cache.debug = True

    logger.debug("Test 2")
    captured = capsys.readouterr()
    output = _parse_output(captured.out)

    assert output.message == "Test 2"
