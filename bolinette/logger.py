import logging


class Logger:
    def __new__(cls):
        _logger = logging.getLogger('internal')
        ch = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        _logger.addHandler(ch)
        return _logger


logger = Logger()
