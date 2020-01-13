import json
import dicttoxml

from bolinette.templating import render


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
        return render('default.html.jinja2', {'response': response})


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
    def __init__(self, serializers=None):
        self.priorities = []
        self.serializers = {}
        if serializers is not None:
            for serializer in serializers:
                self.add(serializer)
    
    def add(self, serializer):
        self.serializers[serializer.mime] = serializer
        self.priorities = sorted(self.priorities + [serializer], key= lambda s: s.priority)
    
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
