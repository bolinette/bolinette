import json_logging
import logging
import sys

from bolinette import core


class Logger:
    def __new__(cls, context: "core.BolinetteContext"):
        if context.env["json_logging"]:
            json_logging.init_non_web(enable_json=True)
        logger = logging.getLogger("test-logger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler(sys.stdout))
        return logger
