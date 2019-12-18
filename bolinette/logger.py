import logging
import sys


class Logger:
    def __new__(cls):
        _logger = logging.getLogger('internal')
        ch = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        _logger.addHandler(ch)
        return _logger


logger = Logger()


class Console:
    def print(self, text):
        print(text)
    
    def error(self, text):
        print(text, file=sys.stderr)


console = Console()
