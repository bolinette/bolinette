import os
import random
import string
from typing import Any

import yaml

from bolinette import abc, console, blnt
from bolinette.exceptions import InitError
from bolinette.utils import paths


class Settings:
    def __init__(self):
        self._settings: dict[str, Any] = {}

    def __getitem__(self, key: str):
        return self._settings.get(key.lower(), None)

    def __contains__(self, key: str):
        return key.lower() in self._settings

    def __setitem__(self, key: str, value):
        self._settings[key.lower()] = value

    def __repr__(self):
        return repr(self._settings)

    def get(self, key: str, default=None):
        item = self[key]
        return item if item is not None else default

    def get_all(self, *, startswith: str = None) -> dict[str, Any]:
        if startswith is not None:
            return dict(((k, v) for k, v in self._settings.items() if k.startswith(startswith)))
        return dict(self._settings)

    @staticmethod
    def _cwd_path(*path):
        return paths.join(paths.cwd(), *path)

    def _reset(self, settings: dict[str, Any]):
        self._settings = {}
        for key, value in settings.items():
            self._settings[key.lower()] = value

    def _flatten_value(self, keys: dict[str, str], prefix: str, value):
        if isinstance(value, dict):
            self._flatten_dict(value, keys=keys, prefix=prefix)
        elif isinstance(value, list):
            for index in range(len(value)):
                self._flatten_value(keys, f'{prefix}-{index}', value[index])
        else:
            keys[prefix.lower()] = value

    def _flatten_dict(self, d: dict, *, keys: dict[str, str] = None, prefix: str = None) -> dict[str, str]:
        keys = keys or {}
        prefix = prefix + '.' if prefix else ''
        for key, value in d.items():
            self._flatten_value(keys, prefix + key, value)
        return keys

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


class Environment(Settings, abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext', *, profile=None, overrides=None):
        Settings.__init__(self)
        abc.WithContext.__init__(self, context)
        profile = profile or init.profile or 'development'
        self._reset(self._merge_env_stack([
            self._load_default_env(),
            self._load_from_file(f'env.{profile}.yaml'),
            self._load_from_file(f'env.local.{profile}.yaml'),
            self._load_from_os(),
            overrides or {},
            {'profile': profile}
        ]))
        self._check_secret_key()

    def _load_default_env(self):
        try:
            with open(self.context.internal_files_path('env', 'default.yaml'), 'r') as f:
                d = yaml.safe_load(f)
                if not isinstance(d, dict):
                    raise yaml.YAMLError()
                return d
        except FileNotFoundError:
            return {}

    @property
    def debug(self):
        return self.get('debug', False)

    @staticmethod
    def _load_from_os():
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
        return self._flatten_dict(settings)

    def _check_secret_key(self):
        if self['secret_key'] is None:
            console.error('Warning: no secret_key set, using random one')
            self['secret_key'] = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
