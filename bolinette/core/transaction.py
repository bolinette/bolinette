import traceback

from sqlalchemy.exc import SQLAlchemyError

from bolinette import core
from bolinette.exceptions import APIError, InternalError
from bolinette.utils import logger


class Transaction:
    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.context.db.session.rollback()
            if not issubclass(exc_type, APIError):
                logger.error(str(exc_val))
                traceback.print_tb(exc_tb)
                raise InternalError([str(exc_val)] + traceback.format_list(traceback.extract_tb(exc_tb)))
        else:
            try:
                self.context.db.session.commit()
            except SQLAlchemyError as err:
                self.context.db.session.rollback()
                raise InternalError([f'global.internal_error:{err}'])
