import json

from flask import request, Response

from bolinette import transaction, marshalling, validate, docs


class Route:
    def __init__(self, func, base_url, url, endpoint, methods, expects, returns):
        self.func = func
        self.base_url = base_url
        self.url = url
        self.endpoint = endpoint
        self.methods = methods
        self.expects = expects
        self.returns = returns
        docs.add_route(self)
    
    def process(self, *args, **kwargs):
        with transaction:
            if self.expects is not None:
                payload = request.get_json(silent=True) or {}
                def_key = f'{self.expects["model"]}.{self.expects["key"]}'
                exp_def = marshalling.get_payload(def_key)
                kwargs['payload'] = validate.payload(
                    exp_def, payload, self.expects.get('patch', False))
                marshalling.link_foreign_entities(exp_def, kwargs['payload'])
            res, code = self.func(*args, **kwargs)
        if self.returns is not None:
            def_key = f'{self.returns["model"]}.{self.returns["key"]}'
            ret_def = marshalling.get_response(def_key)
            if res.get('data') is not None:
                res['data'] = marshalling.marshall(
                    ret_def, res['data'], self.returns.get('skip_none', False),
                    self.returns.get('as_list', False))
        return Response(json.dumps(res), code, mimetype='application/json')
