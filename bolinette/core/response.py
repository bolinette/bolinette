from typing import Union

from aiohttp.web_response import Response as AioResponse
from bolinette.utils import files

from bolinette import core, exceptions


class Cookie:
    def __init__(self, name, value, *, path, http_only=True, expires=None, delete=False):
        self.name = name
        self.value = value
        self.expires = expires
        self.path = path
        self.http_only = http_only
        self.delete = delete


class APIResponse:
    def __init__(self, content, code):
        self.content = content
        self.code = code
        self.cookies = []


class Response:
    def __init__(self, context: 'core.BolinetteContext'):
        self._exceptions = {
            exceptions.UnauthorizedError: self.unauthorized,
            exceptions.BadRequestError: self.bad_request,
            exceptions.ConflictError: self.conflict,
            exceptions.NotFoundError: self.not_found,
            exceptions.ForbiddenError: self.forbidden,
            exceptions.APIError: self.internal_server_error
        }
        self.context = context

    def build_message(self, code, status, messages=None, data=None):
        if messages is None:
            messages = []
        if not isinstance(messages, list):
            messages = [messages]
        body = {
            'code': code,
            'status': status,
            'messages': messages
        }
        if data is not None:
            body['data'] = data
        return APIResponse(body, code)

    def ok(self, messages=None, data=None):
        return self.build_message(200, 'OK', messages, data)

    def created(self, messages=None, data=None):
        return self.build_message(201, 'CREATED', messages, data)

    def bad_request(self, messages=None, data=None):
        return self.build_message(400, 'BAD REQUEST', messages, data)

    def unauthorized(self, messages=None, data=None):
        return self.build_message(401, 'UNAUTHORIZED', messages, data)

    def forbidden(self, messages=None, data=None):
        return self.build_message(403, 'FORBIDDEN', messages, data)

    def not_found(self, messages=None, data=None):
        return self.build_message(404, 'NOT FOUND', messages, data)

    def method_not_allowed(self, messages=None, data=None):
        return self.build_message(405, 'METHOD NOT ALLOWED', messages, data)

    def conflict(self, messages=None, data=None):
        return self.build_message(409, 'CONFLICT', messages, data)

    def internal_server_error(self, messages=None, data=None):
        return self.build_message(500, 'INTERNAL SERVER ERROR', messages, data)

    def render_template(self, name: str, params: dict = None):
        path = self.context.templates_path(f'{name}.jinja2')
        if params is None:
            params = {}
        content = files.render_template(path, params)
        return AioResponse(body=content, status=200, content_type='text/html')

    def from_exception(self, exception: Union[exceptions.APIError, exceptions.APIErrors]):
        messages = []
        if isinstance(exception, exceptions.APIError):
            messages = [exception.message]
        elif isinstance(exception, exceptions.APIErrors):
            messages = [error.message for error in exception.errors]
            exception = exception.errors[0]
        for except_cls in self._exceptions:
            if isinstance(exception, except_cls):
                return self._exceptions[except_cls](messages)
