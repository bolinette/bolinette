from functools import wraps

from sqlalchemy.exc import SQLAlchemyError

from bolinette import db, response
from bolinette.exceptions import APIError


class Transaction:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            db.session.rollback()
            message, code = None, None
            if issubclass(exc_type, APIError):
                message, code = exc_val.response
            if message is not None and code is not None:
                response.abort(message, code)
        else:
            try:
                db.session.commit()
            except SQLAlchemyError as err:
                db.session.rollback()
                response.abort(*response.internal_server_error(f'global.internal_error:{err}'))


transaction = Transaction()


def transactional(func):
    @wraps(func)
    def inner(*args, **kwargs):
        with transaction:
            return func(*args, **kwargs)
    return inner
