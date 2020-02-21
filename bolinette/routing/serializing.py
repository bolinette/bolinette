import json
import dicttoxml
from htmlmin import minify
from flask import request

from bolinette_cli.templating import render


class Serializer:
    def __init__(self, mime, priority):
        self.mime = mime
        self.priority = priority

    def serialize(self, response):
        pass


class HTMLSerializer(Serializer):
    def __init__(self):
        super().__init__('text/html', 0)

    def serialize(self, response):
        return minify(render('default.html.jinja2', {'response': response}))


class JSONSerializer(Serializer):
    def __init__(self):
        super().__init__('application/json', 1)

    def serialize(self, response):
        return json.dumps(response)


class XMLSerializer(Serializer):
    def __init__(self):
        super().__init__('application/xml', 2)

    def serialize(self, response):
        return dicttoxml.dicttoxml(response)


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
    HTMLSerializer(),
    JSONSerializer(),
    XMLSerializer(),
])


def serialize(response):
    mime = request.headers.get('Accept', 'application/json')
    serializer = serializers.get(mime) or serializers.default
    return serializer.serialize(response), serializer.mime
