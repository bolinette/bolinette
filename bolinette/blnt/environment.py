import os
import random
import string
from typing import Dict, Any

import yaml

from bolinette import console, blnt
from bolinette.exceptions import InitError
from bolinette.utils import paths


class Settings:
    def __init__(self):
        self._settings: Dict[str, Any] = {}

    def __getitem__(self, key: str):
        return self._settings.get(key.lower(), None)

    def __contains__(self, key: str):
        return key.lower() in self._settings

    def __setitem__(self, key: str, value):
        self._settings[key.lower()] = value

    def get(self, key: str, default=None):
        item = self[key]
        return item if item is not None else default

    def _cwd_path(self, *path):
        return paths.join(paths.cwd(), *path)

    def _reset(self, settings: Dict[str, Any]):
        self._settings = {}
        for key, value in settings.items():
            self._settings[key.lower()] = value

    def _load_from_file(self, file_name):
        try:
            with open(self._cwd_path('env', file_name), 'r') as f:
                d = yaml.safe_load(f)
                if not isinstance(d, dict):
                    raise yaml.YAMLError()
                return d
        except FileNotFoundError:
            return {}
        except yaml.YAMLError:
            raise InitError(f'File "{file_name}" does not contain valid YAML syntax')


class InitSettings(Settings):
    def __init__(self):
        super().__init__()
        self._DEFAULT_PROFILE = 'development'
        self._init_checks()
        self.profile = self._read_profile()
        self._reset(self._load_from_file('init.yaml'))

    def _read_profile(self):
        if 'BLNT_PROFILE' in os.environ:
            return os.environ['BLNT_PROFILE']
        try:
            with open(self._cwd_path('env', '.profile')) as f:
                profile = f.read().split('\n')[0].strip()
                if not profile:
                    console.error(f'Warning: empty "env/.profile", defaulting to "{self._DEFAULT_PROFILE}"')
                    return self._DEFAULT_PROFILE
                return profile
        except FileNotFoundError:
            console.error(f'Warning: no "env/.profile" file, defaulting to "{self._DEFAULT_PROFILE}"')
            return self._DEFAULT_PROFILE

    def _init_checks(self):
        dirs = [('env',), ('instance',)]
        for d in dirs:
            if not paths.exists(self._cwd_path(*d)):
                console.error(f'Warning: no "{"/".join(d)}" dir, creating one')
                paths.mkdir(self._cwd_path(*d))


init = InitSettings()


class Environment(Settings):
    def __init__(self, context: 'blnt.BolinetteContext', *, profile=None, overrides=None):
        super().__init__()
        self.context = context
        profile = profile or init.profile or 'development'
        self._reset(self._merge_env_stack([
            self._default_env,
            self._load_from_file(f'env.{profile}.yaml'),
            self._load_from_file(f'env.local.{profile}.yaml'),
            self._load_from_os(),
            overrides or {},
            {'profile': profile}
        ]))
        self._check_secret_key()

    @property
    def _default_env(self):
        return {
            'app_name': 'default_name',
            'app_desc': 'default_description',
            'app_version': '0.0.1',
            'database': None,
            'debug': False,
            'host': '127.0.0.1',
            'port': '5000',
            'webapp_folder': self.context.root_path('webapp', 'dist')
        }

    def _load_from_os(self):
        keys = {}
        for key in os.environ:
            if key.startswith('BLNT_'):
                keys[key[5:].lower()] = os.environ[key]
        return keys

    def _merge_env_stack(self, stack):
        settings = {}
        for source in stack:
            for key, value in source.items():
                settings[key.lower()] = value
        return settings

    def _check_secret_key(self):
        if self['secret_key'] is None:
            console.error('Warning: no secret_key set, using random one')
            self['secret_key'] = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
