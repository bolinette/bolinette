from flask import Flask
from flask_cors import CORS
from bolinette_cli import paths

from bolinette import env
from bolinette.database import init_db
from bolinette.jwt import init_jwt
from bolinette.routes import init_routes
from bolinette.documentation import init_docs
from bolinette.errors import init_error_handlers
from bolinette.routing import Namespace
from bolinette.mail import sender


class Bolinette:
    def __init__(self, name, **options):
        profile = options.get('profile')
        env_overrides = options.get('env', {})
        self.app = Flask(name, static_url_path='')
        CORS(self.app, supports_credentials=True)
        env.init_app(self, profile=profile, overrides=env_overrides)
        init_jwt(self.app)
        init_db(self)
        init_routes(self.app)
        init_docs(self.app)
        init_error_handlers(self.app)
        Namespace.init_namespaces(self.app)
        sender.init_app()
