from flask import Blueprint

from bolinette import AccessToken
from bolinette.namespaces import Defaults, Route


class Namespace:
    namespaces = []

    def __init__(self, service, url):
        self.service = service
        self.model = service.name
        self.url = url
        self.blueprint = Blueprint(self.model, __name__, url_prefix='/api' + url)
        self.route = NamespaceRoute(self)

    @staticmethod
    def init_namespaces(app):
        for namespace in Namespace.namespaces:
            app.register_blueprint(namespace)

    def register(self):
        Namespace.namespaces.append(self.blueprint)

    @property
    def defaults(self):
        return Defaults(self)


class NamespaceRoute:
    def __init__(self, namespace):
        self.namespace = namespace

    def __call__(self, rule, **options):
        def inner(func):
            endpoint = options.get('endpoint', func.__name__)
            methods = options.get('methods', ['GET'])
            roles = options.get('roles', [])
            access = options.get('access', (AccessToken.Required if len(roles)
                                            else AccessToken.Optional))
            expects = options.get('expects', None)
            returns = options.get('returns', None)
            route_rules = Route(func, self.namespace.url, rule, endpoint, methods,
                                access, expects, returns, roles)
            self.namespace.blueprint.add_url_rule(
                rule, endpoint, route_rules.process, methods=methods)
            return func

        return inner

    def expects(self, model, key='default', *, patch=False):
        return {
            'model': model,
            'key': key,
            'patch': patch
        }

    def returns(self, model, key='default', *, as_list=False, skip_none=False):
        return {
            'model': model,
            'key': key,
            'as_list': as_list,
            'skip_none': skip_none
        }
