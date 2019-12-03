import os
from configparser import ConfigParser

from bolinette import logger


class Environment:
    @staticmethod
    def keys(app):
        return {
            'APP_NAME': 'DEFAULT_NAME',
            'APP_DESC': 'DEFAULT_DESCRIPTION',
            'APP_VERSION': '0.0.1',
            'DBMS': 'SQLITE',
            'DEBUG': 'True',
            'JWT_SECRET_KEY': '',
            'SECRET_KEY': '',
            'WEBAPP_FOLDER': os.path.join(app.root_path, '..', 'webapp', 'dist')
        }
    
    @staticmethod
    def read_env_file(f):
        return '[DEFAULT]\n' + f.read()

    def __init__(self):
        self.env = {}

    def init(self, app, **options):
        exec_env = options.get('exec_env', 'development')
        overrides = options.get('overrides', {})
        self.env = Environment.keys(app)
        self.env['ENV'] = exec_env
        env_stack = [
            overrides,
            self.load_from_os(),
            self.load_from_file(app, f'{exec_env}.local.env'),
            self.load_from_file(app, f'{exec_env}.env')
        ]
        self.override_env(env_stack)
        self.set_app_config(app)

    def set_app_config(self, app):
        app.config['ENV'] = self.env['ENV']
        debug = self.env.get('DEBUG')
        app.config['DEBUG'] = app.config['ENV'] == 'development' if debug is None \
            else debug == 'True'
        secret_key = self.env.get('SECRET_KEY')
        if secret_key is None or len(secret_key) == 0:
            logger.warning('No secret key set! '
                           'Put this "SECRET_KEY=your_secret_key" '
                           f'in instance/{self.env["ENV"]}.local.env')
        app.secret_key = self.env.get('SECRET_KEY')
        app.static_folder = self.env['WEBAPP_FOLDER']
    
    def load_from_os(self):
        keys = {}
        for key in os.environ:
            if key.startswith('BLNT_'):
                keys[key[5:]] = os.environ[key]
        return keys
    
    def load_from_file(self, app, file_name):
        config = ConfigParser()
        try:
            with open(os.path.join(app.instance_path, file_name), 'r') as f:
                config.read_string(Environment.read_env_file(f))
                if (file_env := config['DEFAULT']) is not None:
                    return file_env
                else:
                    return {}
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
