from functools import wraps

from sqlalchemy.exc import SQLAlchemyError
from bolinette_cli import logger

from bolinette import db, response, serialize
from bolinette.exceptions import APIError


class Transaction:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            db.session.rollback()
            res, code = None, None
            if issubclass(exc_type, APIError):
                res, code = exc_val.response
            else:
                logger.error(str(exc_val))
                res, code = response.internal_server_error(str(exc_val))
            if res is not None and code is not None:
                response.abort(res, code)
        else:
            try:
                db.session.commit()
            except SQLAlchemyError as err:
                db.session.rollback()
                res, code = response.internal_server_error(f'global.internal_error:{err}')
                response.abort(res, code)


transaction = Transaction()
