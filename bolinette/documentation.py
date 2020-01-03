import json

from flask import Blueprint, Response

from bolinette import marshalling


class Documentation:
    def __init__(self):
        self.app = None
        self.routes = []

    def add_route(self, route):
        self.routes.append(route)

    def process_definition(self, key, get_func):
        if isinstance(key, str):
            definition = get_func(key)
        else:
            definition = get_func(f'{key["model"]}.{key["key"]}')
        ret = {}
        for field in definition.fields:
            if isinstance(field, marshalling.Field):
                ret[field.name] = str(field.type)
            elif isinstance(field, marshalling.Definition):
                ret[field.name] = self.process_definition(field.key, get_func)
            elif isinstance(field, marshalling.List):
                ret[field.name] = [self.process_definition(field.element.key, get_func)]
        return ret

    def process_payload(self, expects):
        return self.process_definition(expects, marshalling.get_payload)

    def process_response(self, returns):
        return self.process_definition(returns, marshalling.get_response)

    def process_docs(self):
        ret = {}
        for route in self.routes:
            doc = route.func.__doc__
            if isinstance(doc, str):
                doc = doc.strip()
            if route.base_url not in ret:
                ret[route.base_url] = {}
            if route.url not in ret[route.base_url]:
                ret[route.base_url][route.url] = {}
            expects = route.expects
            if expects is not None:
                expects = self.process_payload(expects)
            returns = route.returns
            if returns is not None:
                returns = self.process_response(returns)
            for method in route.methods:
                ret[route.base_url][route.url][method.lower()] = {
                    'doc': doc,
                    'expects': expects,
                    'returns': returns
                }
        return ret


docs = Documentation()


def init_docs(app):
    def inner():
        return Response(json.dumps(docs.process_docs()), 200, mimetype='application/json')
    docs.app = app
    blueprint = Blueprint('bolinette_docs', __name__, url_prefix='/docs')
    blueprint.add_url_rule('', 'bolinette_docs', inner, methods=['GET'])
    app.register_blueprint(blueprint)
