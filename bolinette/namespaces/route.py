import inspect

from flask import request, Response
from flask_sqlalchemy import Pagination

from bolinette import transaction, marshalling, validate, docs, AccessToken
from bolinette.namespaces import serialize


class Route:
    @staticmethod
    def _func_accepts_keywords(func):
        return any(param for param in inspect.signature(func).parameters.values() if param.kind == param.VAR_KEYWORD)

    def __init__(self, func, base_url, url, endpoint, methods, access, expects, returns, roles):
        self.func = func
        self.base_url = base_url
        self.url = url
        self.endpoint = endpoint
        self.methods = methods
        self.access = access
        self.expects = expects
        self.returns = returns
        self.roles = roles
        docs.add_route(self)

    def process(self, *args, **kwargs):
        self.access.check(self.roles)
        payload = request.get_json(silent=True) or {}
        if len(request.args) and Route._func_accepts_keywords(self.func):
            kwargs['args'] = dict(request.args)
        with transaction:
            if self.expects is not None:
                def_key = f'{self.expects["model"]}.{self.expects["key"]}'
                exp_def = marshalling.get_payload(def_key)
                kwargs['payload'] = validate.payload(
                    exp_def, payload, self.expects.get('patch', False))
                marshalling.link_foreign_entities(exp_def, kwargs['payload'])

            res, code = self.func(*args, **kwargs)

        if res.get('data') is not None and isinstance(res['data'], Pagination):
            res['pagination'] = {
                'page': res['data'].page,
                'per_page': res['data'].per_page,
                'total': res['data'].total,
            }
            res['data'] = res['data'].items

        if self.returns is not None:
            def_key = f'{self.returns["model"]}.{self.returns["key"]}'
            ret_def = marshalling.get_response(def_key)
            if res.get('data') is not None:
                res['data'] = marshalling.marshall(
                    ret_def, res['data'], self.returns.get('skip_none', False),
                    self.returns.get('as_list', False))

        res, mime = serialize(res)
        return Response(res, code, mimetype=mime)
