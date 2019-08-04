import json
from functools import wraps

from flask import Blueprint, Response

from flasque import app


class Namespace:
    def __init__(self, name, url):
        self.blueprint = Blueprint(name, __name__, url_prefix='/api' + url)

    def route(self, rule, **options):
        def wrapper(func):
            endpoint = options.pop("endpoint", func.__name__)
            self.blueprint.add_url_rule(rule, endpoint, func, **options)
            @wraps(func)
            def inner(*args, **kwargs):
                res, code = func(*args, **kwargs)
                return Response(json.dumps(res), code, mimetype='application/json')
            return inner
        return wrapper

    def register(self):
        app.register_blueprint(self.blueprint)
