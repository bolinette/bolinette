import traceback

from sqlalchemy.exc import SQLAlchemyError

from bolinette import types
from bolinette.exceptions import APIError, InternalError
from bolinette.utils import logger


class Transaction:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            types.engine.session.rollback()
            if not issubclass(exc_type, APIError):
                logger.error(str(exc_val))
                traceback.print_tb(exc_tb)
                raise InternalError([str(exc_val)])
        else:
            try:
                types.engine.session.commit()
            except SQLAlchemyError as err:
                types.engine.session.rollback()
                raise InternalError([f'global.internal_error:{err}'])


transaction = Transaction()
