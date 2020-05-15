import datetime
import json

from aiohttp.web_request import Request


async def deserialize(request: Request):
    content_type = request.content_type
    if content_type == 'application/json':
        return await request.json()
    if content_type == 'multipart/form-data':
        return await request.post()
    return {}


class Serializer:
    def __init__(self, mime, priority):
        self.mime = mime
        self.priority = priority

    def serialize(self, response):
        pass


class JSONSerializer(Serializer):
    def __init__(self):
        super().__init__('application/json', 1)

    @staticmethod
    def _json_type_converter(o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        return o

    def serialize(self, response):
        return json.dumps(response, default=JSONSerializer._json_type_converter)


class Serializers:
    def __init__(self, functions=None):
        self.priorities = []
        self.serializers = {}
        if functions is not None:
            for serializer in functions:
                self.add(serializer)

    def add(self, serializer):
        self.serializers[serializer.mime] = serializer
        self.priorities = sorted(self.priorities + [serializer], key=lambda s: s.priority)

    def get(self, mime):
        return self.serializers.get(mime, None)

    @property
    def default(self):
        return self.priorities[0]


serializers = Serializers([
    JSONSerializer(),
])


def serialize(response, mime):
    serializer = serializers.get(mime) or serializers.default
    return serializer.serialize(response), serializer.mime
