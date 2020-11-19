import traceback

from sqlalchemy.exc import SQLAlchemyError

from bolinette import blnt
from bolinette.exceptions import APIError, APIErrors, InternalError


class Transaction:
    def __init__(self, context: 'blnt.BolinetteContext'):
        self.context = context

    async def __aenter__(self):
        await self.context.db.open_transaction()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.context.db.rollback_transaction()
            if not issubclass(exc_type, (APIError, APIErrors)):
                self.context.logger.error(str(exc_val))
                traceback.print_tb(exc_tb)
                if self.context.env['debug']:
                    raise InternalError([str(exc_val)] + traceback.format_list(traceback.extract_tb(exc_tb)))
                raise InternalError('internal.error')
        else:
            try:
                await self.context.db.close_transaction()
            except SQLAlchemyError as err:
                await self.context.db.rollback_transaction()
                raise InternalError([f'global.internal_error:{err}'])
