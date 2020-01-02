import json

from flask import Blueprint, Response


class Documentation:
    def __init__(self):
        self.app = None
        self.routes = []

    def add_route(self, route):
        self.routes.append(route)


docs = Documentation()


def init_docs(app):
    def inner():
        return Response(json.dumps([route.doc for route in docs.routes]), 200, mimetype='application/json')
    docs.app = app
    blueprint = Blueprint('bolinette_docs', __name__, url_prefix='/docs')
    blueprint.add_url_rule('', 'bolinette_docs', inner, methods=['GET'])
    app.register_blueprint(blueprint)
