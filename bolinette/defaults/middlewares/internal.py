from collections.abc import Callable, Awaitable
from typing import Any

from aiohttp import web as aio_web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bolinette import web, blnt
from bolinette.blnt.objects import Pagination, PaginationParams, OrderByParams
from bolinette.decorators import middleware
from bolinette.exceptions import BadRequestError
from bolinette.utils.serializing import deserialize, serialize


@middleware('blnt_payload', priority=60, auto_load=False, loadable=False)
class PayloadMiddleware(web.InternalMiddleware):
    def define_options(self):
        return {
            'model': self.params.string(),
            'key': self.params.string(),
            'patch': self.params.bool()
        }

    async def handle(self, request, params, next_func):
        try:
            payload = await deserialize(request)
        except Exception:
            raise BadRequestError('global.payload.unserializable')
        if self.options['model'] is not None and self.options['key'] is not None:
            payload = await self.context.validator.validate_payload(self.options['model'], self.options['key'],
                                                                    payload, self.options['patch'])
        params['payload'] = payload
        return await next_func(request, params)


@middleware('blnt_response', priority=40, auto_load=False, loadable=False)
class ResponseMiddleware(web.InternalMiddleware):
    def define_options(self):
        return {
            'model': self.params.string(),
            'key': self.params.string(),
            'as_list': self.params.bool(),
            'skip_none': self.params.bool()
        }

    async def handle(self, request, params, next_func):
        async with blnt.Transaction(self.context):
            resp = await next_func(request, params)
        if resp is None:
            return aio_web.Response(status=204)
        elif isinstance(resp, aio_web.Response):
            return resp
        elif isinstance(resp, str):
            return aio_web.Response(text=resp, status=200, content_type='text/plain')
        elif not isinstance(resp, web.APIResponse):
            if self.options['model'] is not None:
                resp = web.Response(self.context).ok(data=resp)
            else:
                return aio_web.Response(text='global.response.unserializable', status=500, content_type='text/plain')

        content = resp.content

        if content.get('data') is not None and isinstance(content['data'], Pagination):
            content['pagination'] = {
                'page': content['data'].page,
                'per_page': content['data'].per_page,
                'total': content['data'].total
            }
            content['data'] = content['data'].items

        if self.options['model'] is not None:
            ret_def = self.context.mapper.response(self.options['model'], self.options['key'])
            if content.get('data') is not None:
                content['data'] = self.context.mapper.marshall(ret_def, content['data'],
                                                               skip_none=self.options.get('skip_none', False),
                                                               as_list=self.options.get('as_list', False))

        serialized, mime = serialize(content, 'application/json')

        web_response = aio_web.Response(text=serialized, status=resp.code, content_type=mime)
        for cookie in resp.cookies:
            if not cookie.delete:
                expires = None
                if cookie.expires:
                    expires = cookie.expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
                web_response.set_cookie(cookie.name, cookie.value,
                                        expires=expires,
                                        path=cookie.path, httponly=cookie.http_only)
            else:
                web_response.del_cookie(cookie.name, path=cookie.path)

        return web_response


@middleware('blnt_headers', priority=10, auto_load=True, loadable=False)
class HeadersMiddleware(web.InternalMiddleware):
    async def handle(self, request: Request, params: dict[str, Any],
                     next_func: Callable[[Request, dict[str, Any]], Awaitable[Response]]):
        params['headers'] = {}
        for key in request.headers:
            params['headers'][key] = request.headers[key]
        return await next_func(request, params)


@middleware('blnt_query_pagination', priority=30, auto_load=True, loadable=False)
class PaginationMiddleware(web.InternalMiddleware):
    async def handle(self, request: Request, params: dict[str, Any],
                     next_func: Callable[[Request, dict[str, Any]], Awaitable[Response]]):
        if 'page' in request.query or 'per_page' in request.query:
            try:
                page = int(request.query.get('page', "0"))
                per_page = int(request.query.get('per_page', "20"))
            except ValueError:
                raise BadRequestError('global.pagination.param_not_number')
            params['pagination'] = PaginationParams(page, per_page)
        return await next_func(request, params)


@middleware('blnt_query_order_by', priority=30, auto_load=True, loadable=False)
class OrderByMiddleware(web.InternalMiddleware):
    async def handle(self, request: Request, params: dict[str, Any],
                     next_func: Callable[[Request, dict[str, Any]], Awaitable[Response]]):
        if 'order_by' in request.query:
            order_by = []
            columns = request.query['order_by'].split(',')
            for column in columns:
                col_name, *col_args = column.split(':')
                order_way = col_args[0] if len(col_args) > 0 else 'asc'
                order_by.append(OrderByParams(col_name, order_way == 'asc'))
            params['order_by'] = order_by
        return await next_func(request, params)
