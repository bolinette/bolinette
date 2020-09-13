import os
from typing import Dict, Any

import yaml
from bolinette_common import paths, console

from bolinette import core
from bolinette.exceptions import InitError


class Settings:
    def __init__(self):
        self._settings: Dict[str, Any] = {}

    def __getitem__(self, key: str):
        return self._settings.get(key.lower(), None)

    def __contains__(self, key: str):
        return key.lower() in self._settings

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
                    raise InitError(inner=TypeError(f"'{file_name}' does not contain valid YAML syntax"))
                return d
        except FileNotFoundError:
            return {}


class InitSettings(Settings):
    def __init__(self):
        super().__init__()
        self._DEFAULT_PROFILE = 'development'
        self._init_checks()
        self.profile = self._read_profile()
        self._reset(self._load_from_file('init.yaml'))

    def _read_profile(self):
        try:
            with open(self._cwd_path('env', '.profile')) as f:
                profile = f.read().split('\n')[0].strip()
                if not profile:
                    console.error(f"Warning: empty 'env/.profile', defaulting to '{self._DEFAULT_PROFILE}'")
                    return self._DEFAULT_PROFILE
                return profile
        except FileNotFoundError:
            console.error(f"Warning: no 'env/.profile' file, defaulting to '{self._DEFAULT_PROFILE}'")
            return self._DEFAULT_PROFILE

    def _init_checks(self):
        dirs = [('env',), ('instance',)]
        for d in dirs:
            if not paths.exists(self._cwd_path(*d)):
                console.error(f"Warning: no '{'/'.join(d)}' dir, creating one")
                paths.mkdir(self._cwd_path(*d))


init = InitSettings()


class Environment(Settings):
    def __init__(self, context: 'core.BolinetteContext', *, profile=None, overrides=None):
        super().__init__()
        self.context = context
        profile = profile or init.profile or 'development'
        self._reset(self.merge_env_stack([
            self.default_env,
            self._load_from_file(f'env.{profile}.yaml'),
            self._load_from_file(f'env.local.{profile}.yaml'),
            self.load_from_os(),
            overrides or {},
            {'profile': profile}
        ]))

    @property
    def default_env(self):
        return {
            'APP_NAME': 'DEFAULT_NAME',
            'APP_DESC': 'DEFAULT_DESCRIPTION',
            'APP_VERSION': '0.0.1',
            'DBMS': 'SQLITE',
            'DEBUG': True,
            'HOST': '127.0.0.1',
            'PORT': '5000',
            'WEBAPP_FOLDER': self.context.root_path('webapp', 'dist')
        }

    def load_from_os(self):
        keys = {}
        for key in os.environ:
            if key.startswith('BLNT_'):
                keys[key[5:]] = os.environ[key]
        return keys

    def merge_env_stack(self, stack):
        settings = {}
        for source in stack:
            for key, value in source.items():
                settings[key.lower()] = value
        return settings
