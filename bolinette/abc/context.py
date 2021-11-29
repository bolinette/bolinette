from abc import ABC
from typing import Any

from bolinette import abc
from bolinette.utils import paths


class Context(ABC):
    def __init__(self, origin: str, *,
                 env: 'abc.Environment',
                 inject: 'abc.inject.Injection',
                 db: 'abc.db.Manager',
                 mapper: 'abc.mapping.Mapper',
                 resources: 'abc.web.Resources'):
        self._ctx: dict[str, Any] = {}
        self._origin = origin
        self._cwd = paths.cwd()
        self.env = env
        self.inject = inject
        self.db = db
        self.mapper = mapper
        self.resources = resources
        self.manifest: dict[str, Any] = {}

    def __getitem__(self, key: str):
        if key not in self._ctx:
            raise KeyError(f'No {key} element registered in context')
        return self._ctx[key]

    def __setitem__(self, key: str, value: Any):
        self._ctx[key] = value

    def __delitem__(self, key: str):
        if key not in self._ctx:
            raise KeyError(f'No {key} element registered in context')
        del self._ctx[key]

    def __contains__(self, key: str):
        return key in self._ctx

    def internal_path(self, *path):
        return paths.join(self._origin, *path)

    def internal_files_path(self, *path):
        return paths.join(self._origin, '_files', *path)

    def root_path(self, *path):
        return paths.join(self._cwd, *path)

    def instance_path(self, *path):
        return self.root_path('instance', *path)

    def env_path(self, *path):
        return self.root_path('env', *path)

    def static_path(self, *path):
        return self.root_path('static', *path)

    def templates_path(self, *path):
        return self.root_path('templates', *path)


class WithContext(ABC):
    def __init__(self, context: Context, **kwargs):
        self.__blnt_ctx__ = context

    @property
    def context(self):
        return self.__blnt_ctx__
