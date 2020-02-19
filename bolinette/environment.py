import os
import yaml

from bolinette_cli import logger, parser, paths


class Settings:
    def __init__(self):
        self.settings = {}

    def __getitem__(self, key):
        return self.settings.get(key.lower(), None)

    def __setitem__(self, key, value):
        self.settings[key.lower()] = value

    def get(self, key, default=None):
        item = self[key]
        return item if item is not None else default

    def reset(self, settings):
        self.settings = {}
        for key, value in settings.items():
            self[key] = value


class Environment(Settings):
    def __init__(self):
        super().__init__()
        self.cwd = paths.cwd()
        self.origin = paths.dirname(__file__)
        self.init = Settings()
        self.init.reset(self.load_from_file('init.yaml'))

    def instance_path(self, *path):
        return self.root_path('instance', *path)

    def root_path(self, *path):
        return paths.join(self.cwd, *path)

    def internal_path(self, *path):
        return paths.join(self.origin, *path)

    @property
    def default_env(self):
        return {
            'APP_NAME': 'DEFAULT_NAME',
            'APP_DESC': 'DEFAULT_DESCRIPTION',
            'APP_VERSION': '0.0.1',
            'DBMS': 'SQLITE',
            'DEBUG': True,
            'FLASK_HOST': '127.0.0.1',
            'FLASK_PORT': '5000',
            'WEBAPP_FOLDER': self.root_path('webapp', 'dist')
        }

    def read_profile(self):
        try:
            with open(self.instance_path('.profile')) as f:
                for line in f:
                    return line.strip().replace('\n', '')
        except FileNotFoundError:
            return None

    def init_app(self, bolinette, **options):
        profile = options.get('profile') or self.read_profile() or 'development'
        overrides = options.get('overrides', {})
        self.reset(self.merge_env_stack([
            self.default_env,
            self.load_from_file(f'env.{profile}.yaml'),
            self.load_from_file(f'env.local.{profile}.yaml'),
            self.load_from_os(),
            overrides,
            {'profile': profile}
        ]))
        self.set_app_config(bolinette.app)

    def set_app_config(self, app):
        app.config['ENV'] = self['PROFILE']
        debug = self['DEBUG']
        app.config['DEBUG'] = self['PROFILE'] == 'development' if debug is None else debug
        secret_key = self['SECRET_KEY']
        if secret_key is None or len(secret_key) == 0:
            logger.warning('No secret key set! '
                           'Put this "SECRET_KEY=your_secret_key" '
                           f'in instance/{self["PROFILE"]}.local.env')
        app.secret_key = self['SECRET_KEY']
        app.static_folder = self['WEBAPP_FOLDER']

    def load_from_os(self):
        keys = {}
        for key in os.environ:
            if key.startswith('BLNT_'):
                keys[key[5:]] = os.environ[key]
        return keys

    def load_from_file(self, file_name):
        try:
            with open(self.instance_path(file_name), 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}

    def merge_env_stack(self, stack):
        settings = {}
        for source in stack:
            for key, value in source.items():
                settings[key.lower()] = value
        return settings


env = Environment()
