from datetime import datetime

from bolinette import abc, web
from bolinette.decorators import middleware, injected
from bolinette.exceptions import InternalError
from example.services import TraceService


@middleware('tracking')
class TrackingMiddleware(web.Middleware):
    def define_options(self):
        return {
            'name': self.params.string(required=True)
        }

    @injected
    def trace_service(self, inject: abc.inject.Injection):
        return inject.require(TraceService)

    async def handle(self, request, params, next_func):
        if 'current_user' not in params:
            raise InternalError('auth middleware needs to be called before tracking middleware')
        current_user = params['current_user']
        page_name = self.options['name']
        await self.trace_service.inc_trace(page_name, current_user, datetime.utcnow())
        return await next_func(request, params)
