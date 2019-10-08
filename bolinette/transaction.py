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
                if exc_val.type == APIError.Type.BAD_REQUEST:
                    message, code = response.bad_request(exc_val.messages)
                if exc_val.type == APIError.Type.CONFLICT:
                    message, code = response.conflict(exc_val.messages)
                if exc_val.type == APIError.Type.NOT_FOUND:
                    message, code = response.not_found(exc_val.messages)
            if message is not None and code is not None:
                response.abort(message, code)
        else:
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                response.abort(*response.internal_server_error('global.internal_error'))


transaction = Transaction()


def transactional(func):
    @wraps(func)
    def inner(*args, **kwargs):
        with transaction:
            return func(*args, **kwargs)
    return inner
