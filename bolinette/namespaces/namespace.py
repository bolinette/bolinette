import json

from flask import Blueprint, Response

from bolinette.namespaces import Defaults, Route


class Namespace:
    namespaces = []

    def __init__(self, service, url):
        self.service = service
        self.model = service.name
        self.url = url
        self.blueprint = Blueprint(self.model, __name__, url_prefix='/api' + url)

    @staticmethod
    def init_namespaces(app):
        for namespace in Namespace.namespaces:
            app.register_blueprint(namespace)

    def route(self, rule, **options):
        def inner(func):
            endpoint = options.get('endpoint', func.__name__)
            methods = options.get('methods', ['GET'])
            expects = options.get('expects', None)
            returns = options.get('returns', None)
            route_rules = Route(func, self.url, rule, endpoint, methods, expects, returns)
            self.blueprint.add_url_rule(rule, endpoint, route_rules.process, methods=methods)
            return func

        return inner

    def register(self):
        Namespace.namespaces.append(self.blueprint)
    
    @property
    def defaults(self):
        return Defaults(self)
