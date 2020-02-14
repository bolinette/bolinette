import os
from configparser import ConfigParser

from bolinette_cli import logger, parser


class Environment:
    @staticmethod
    def keys(bolinette):
        return {
            'APP_NAME': 'DEFAULT_NAME',
            'APP_DESC': 'DEFAULT_DESCRIPTION',
            'APP_VERSION': '0.0.1',
            'DBMS': 'SQLITE',
            'DB_URL': '',
            'DEBUG': 'True',
            'FLASK_HOST': '127.0.0.1',
            'FLASK_PORT': '5000',
            'JWT_SECRET_KEY': '',
            'SECRET_KEY': '',
            'USER_EMAIL_REQUIRED': False,
            'WEBAPP_FOLDER': bolinette.root_path('webapp', 'dist')
        }

    @staticmethod
    def read_env_file(f):
        return '[DEFAULT]\n' + f.read()

    def __init__(self):
        self.env = {}

    def init(self, bolinette, **options):
        profile = options.get('profile') or 'development'
        overrides = options.get('overrides', {})
        self.env = Environment.keys(bolinette)
        self.env['PROFILE'] = profile
        env_stack = [
            overrides,
            self.load_from_os(),
            self.load_from_file(bolinette, f'{profile}.local.env'),
            self.load_from_file(bolinette, f'{profile}.env')
        ]
        self.override_env(env_stack)
        self.set_app_config(bolinette.app)

    def set_app_config(self, app):
        app.config['ENV'] = self.env['PROFILE']
        debug = self.env.get('DEBUG')
        app.config['DEBUG'] = self.env['PROFILE'] == 'development' if debug is None \
            else debug == 'True'
        secret_key = self.env.get('SECRET_KEY')
        if secret_key is None or len(secret_key) == 0:
            logger.warning('No secret key set! '
                           'Put this "SECRET_KEY=your_secret_key" '
                           f'in instance/{self.env["PROFILE"]}.local.env')
        app.secret_key = self.env.get('SECRET_KEY')
        app.static_folder = self.env['WEBAPP_FOLDER']

    def load_from_os(self):
        keys = {}
        for key in os.environ:
            if key.startswith('BLNT_'):
                keys[key[5:]] = os.environ[key]
        return keys

    def load_from_file(self, bolinette, file_name):
        config = ConfigParser()
        try:
            with open(bolinette.instance_path(file_name), 'r') as f:
                config.read_string(Environment.read_env_file(f))
                return config['DEFAULT'] or {}
        except FileNotFoundError:
            return {}

    def override_env(self, stack):
        for key in self.env:
            override = self.parse_sources(key, stack)
            if override is not None:
                self.env[key] = override

    def parse_sources(self, key, stack):
        for source in stack:
            if key in source:
                return source[key]
        return None

    def __getitem__(self, key):
        return self.env.get(key, None)

    def __setitem__(self, key, value):
        self.env[key] = value

    def get(self, key, default=None):
        item = self[key]
        return item if item is not None else default


env = Environment()
