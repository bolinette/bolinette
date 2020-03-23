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


response = Response()
