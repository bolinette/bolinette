import json_logging
import logging
import sys


class Logger:
    def __new__(cls):
        json_logging.init_non_web(enable_json=True)
        logger = logging.getLogger("test-logger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler(sys.stdout))
        return logger
