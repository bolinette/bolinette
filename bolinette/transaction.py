import traceback

from sqlalchemy.exc import SQLAlchemyError

from bolinette import response, db
from bolinette.exceptions import APIError, AbortRequestException
from bolinette.utils import logger


class Transaction:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            db.engine.session.rollback()
            if issubclass(exc_type, APIError):
                res = exc_val.response
            else:
                logger.error(str(exc_val))
                res = response.internal_server_error(str(exc_val))
                traceback.print_tb(exc_tb)
            raise AbortRequestException(res)
        else:
            try:
                db.engine.session.commit()
            except SQLAlchemyError as err:
                db.engine.session.rollback()
                res = response.internal_server_error(f'global.internal_error:{err}')
                raise AbortRequestException(res)


transaction = Transaction()
