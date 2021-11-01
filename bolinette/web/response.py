from aiohttp.web_response import Response as AioResponse
from jinja2 import TemplateNotFound

from bolinette.utils import files, paths

from bolinette import abc, blnt, exceptions


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


class Response(abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self._exceptions = {
            exceptions.UnauthorizedError: self.unauthorized,
            exceptions.BadRequestError: self.bad_request,
            exceptions.UnprocessableEntityError: self.unprocessable_entity,
            exceptions.ConflictError: self.conflict,
            exceptions.NotFoundError: self.not_found,
            exceptions.ForbiddenError: self.forbidden,
            exceptions.APIError: self.internal_server_error
        }

    @staticmethod
    def _build_message(code, status, messages=None, data=None):
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

    def ok(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(200, 'OK', messages, data)

    def created(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(201, 'CREATED', messages, data)

    def bad_request(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(400, 'BAD REQUEST', messages, data)

    def unauthorized(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(401, 'UNAUTHORIZED', messages, data)

    def forbidden(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(403, 'FORBIDDEN', messages, data)

    def not_found(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(404, 'NOT FOUND', messages, data)

    def method_not_allowed(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(405, 'METHOD NOT ALLOWED', messages, data)

    def conflict(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(409, 'CONFLICT', messages, data)

    def unprocessable_entity(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(422, 'UNPROCESSABLE ENTITY', messages, data)

    def internal_server_error(self, *, messages: str | list[str] | None = None, data=None):
        return self._build_message(500, 'INTERNAL SERVER ERROR', messages, data)

    def render_template(self, name: str, params: dict = None, workdir: str = None, *, status=200):
        if workdir is None:
            workdir = self.context.templates_path()
        if params is None:
            params = {}
        for key, value in self.context.manifest.items():
            if key not in params:
                params[key] = value
        try:
            content = files.render_template(workdir, name, params)
        except TemplateNotFound:
            error_404_wd = self.context.internal_files_path('templates')
            error_404 = paths.join('errors', '404.html.jinja2')
            content = files.render_template(error_404_wd, error_404, params)
            status = 404
        return AioResponse(body=content, status=status, content_type='text/html')

    def from_exception(self, exception: exceptions.APIError | exceptions.APIErrors):
        messages = []
        if isinstance(exception, exceptions.APIError):
            messages = [str(exception)]
        elif isinstance(exception, exceptions.APIErrors):
            messages = [str(error) for error in exception.errors]
            exception = exception.errors[0]
        for except_cls in self._exceptions:
            if isinstance(exception, except_cls):
                return self._exceptions[except_cls](messages=messages)
