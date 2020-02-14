from flask import Flask
from flask_cors import CORS
from bolinette_cli import paths

from bolinette import env, Namespace
from bolinette.database import init_db
from bolinette.jwt import init_jwt
from bolinette.routes import init_routes
from bolinette.documentation import init_docs
from bolinette.errors import init_error_handlers


class Bolinette:
    def __init__(self, name, **options):
        self.cwd = paths.cwd()
        self.origin = paths.dirname(__file__)
        profile = options.get('profile')
        env_overrides = options.get('env', {})
        self.app = Flask(name, static_url_path='')
        CORS(self.app, supports_credentials=True)
        env.init(self, profile=profile, overrides=env_overrides)
        init_jwt(self.app)
        init_db(self)
        init_routes(self.app)
        init_docs(self.app)
        init_error_handlers(self.app)
        Namespace.init_namespaces(self.app)

    def instance_path(self, *path):
        return self.root_path('instance', *path)

    def root_path(self, *path):
        return paths.join(self.cwd, *path)

    def internal_path(self, *path):
        return paths.join(self.origin, *path)
