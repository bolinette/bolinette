import traceback

from sqlalchemy.exc import SQLAlchemyError

from bolinette.data import DataContext
from bolinette.exceptions import APIError, APIErrors, InternalError


class Transaction:
    def __init__(
        self,
        data_ctx: DataContext,
        *,
        print_error: bool = True,
        propagate_error: bool = True,
        raise_internal: bool = True,
    ):
        self._data_ctx = data_ctx
        self._context = data_ctx.context
        self.print_error = print_error
        self.propagate_error = propagate_error
        self.raise_internal = raise_internal

    async def __aenter__(self):
        await self._data_ctx.db.open_transaction()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self._data_ctx.db.rollback_transaction()
            if not issubclass(exc_type, (APIError, APIErrors)):
                if self.print_error:
                    self._context.logger.error(str(exc_val))
                    traceback.print_tb(exc_tb)
                if self.propagate_error and self.raise_internal:
                    if self._context.env["debug"]:
                        raise InternalError(
                            "".join(
                                [str(exc_val)]
                                + traceback.format_list(traceback.extract_tb(exc_tb))
                            )
                        )
                    raise InternalError("internal.error")
                elif self.propagate_error:
                    raise exc_val
        else:
            try:
                await self._data_ctx.db.close_transaction()
            except SQLAlchemyError as err:
                await self._data_ctx.db.rollback_transaction()
                raise InternalError(f"global.internal_error:{err}")
