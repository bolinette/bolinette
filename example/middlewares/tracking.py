from datetime import datetime

from bolinette import web
from bolinette.decorators import middleware
from bolinette.exceptions import InternalError
from example.services import TraceService


@middleware('tracking')
class TrackingMiddleware(web.Middleware):
    def define_options(self):
        return {
            'name': self.params.string(required=True)
        }

    @property
    def trace_service(self) -> TraceService:
        return self.context.service('trace')

    async def handle(self, request, params, next_func):
        if 'current_user' not in params:
            raise InternalError('auth middleware needs to be called before tracking middleware')
        current_user = params['current_user']
        page_name = self.options['name']
        await self.trace_service.inc_trace(page_name, current_user, datetime.utcnow())
        return await next_func(request, params)
