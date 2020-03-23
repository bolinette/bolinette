from typing import List, AnyStr

from bolinette.routing import Route, Method, AccessType, resources
from bolinette.routing.defaults import Defaults


class Namespace:
    def __init__(self, base_url, service):
        self.base_url = base_url
        self.service = service
        self.model = service.name
        self.route = NamespaceRoute(self)

    @property
    def defaults(self):
        return Defaults(self)


class NamespaceExcepts:
    def __init__(self, model, key='default', *, patch=False):
        self.model = model
        self.key = key
        self.patch = patch


class NamespaceReturns:
    def __init__(self, model, key='default', *, as_list=False, skip_none=False):
        self.model = model
        self.key = key
        self.as_list = as_list
        self.skip_none = skip_none


class NamespaceRoute:
    def __init__(self, namespace):
        self.namespace = namespace

    def __call__(self, path, *, method: Method,
                 access: AccessType = None, expects: NamespaceExcepts = None,
                 returns: NamespaceReturns = None, roles: List[AnyStr] = None):
        def inner(func):
            route = Route(func=func, base_url=self.namespace.base_url, path=path, method=method,
                          access=access, expects=expects, returns=returns, roles=roles)
            resources.register(route)
            return func
        return inner

    def expects(self, model, key='default', *, patch=False):
        return NamespaceExcepts(model, key, patch=patch)

    def returns(self, model, key='default', *, as_list=False, skip_none=False):
        return NamespaceReturns(model, key, as_list=as_list, skip_none=skip_none)
