import os
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from bolinette.core import Cache, Logger, __user_cache__, meta
from bolinette.core.exceptions import EnvironmentError
from bolinette.core.injection import Injection, init_method
from bolinette.core.mapping import Mapper
from bolinette.core.utils import FileUtils, PathUtils


class _EnvSectionMeta:
    def __init__(self, name: str) -> None:
        self.name = name


class Environment:
    _OS_ENV_PREFIX = "BLNT_"

    def __init__(
        self,
        profile: str,
        logger: "Logger[Environment]",
        cache: Cache,
        inject: Injection,
        paths: PathUtils,
        files: FileUtils,
        mapper: Mapper,
        *,
        env_path: str = "env",
    ) -> None:
        self._profile = profile
        self._logger = logger
        self._cache = cache
        self._inject = inject
        self._paths = paths
        self._files = files
        self._mapper = mapper
        self._path = env_path
        self._raw_env: dict[str, Any] = {}

    def _init_section(self, section: object) -> None:
        section_name = meta.get(type(section), _EnvSectionMeta).name
        if section_name not in self._raw_env:
            raise EnvironmentError(f"No '{section_name}' section was found in the environment files")
        self._mapper.map(
            dict[str, Any],
            type(section),
            self._raw_env[section_name],
            section,
            src_path=f"Environment['{section_name}']",
        )

    @init_method
    def init(self) -> None:
        if EnvironmentSection in self._cache:
            for cls in self._cache.get(EnvironmentSection, hint=type):
                self._inject.add(cls, "singleton", before_init=[self._init_section])

        stack = [
            self._init_from_os(),
            self._init_from_file("env.yaml"),
            self._init_from_file(f"env.{self._profile}.yaml"),
            self._init_from_file(f"env.local.{self._profile}.yaml"),
        ]

        merged: dict[str, Any] = {}
        for node in stack:
            for name, section in node.items():
                if name not in merged:
                    merged[name] = {}
                for key, value in section.items():
                    merged[name][key] = value
        self._raw_env = merged

    @staticmethod
    def _init_from_os() -> dict[str, dict[str, Any]]:
        _vars: dict[str, str] = {}
        prefix_len = len(Environment._OS_ENV_PREFIX)
        for var in os.environ:
            if var.startswith(Environment._OS_ENV_PREFIX):
                _vars[var[prefix_len:]] = os.environ[var]
        _env: dict[str, Any] = {}
        for key, value in _vars.items():
            path = [s.lower() for s in key.split("__")]
            _node = _env
            for p in path[:-1]:
                if p not in _node:
                    _node[p] = {}
                _node = _node[p]
            if not isinstance(_node, dict) or path[-1] in _node:
                raise EnvironmentError(
                    f"OS variable '{Environment._OS_ENV_PREFIX}{key}' conflicts with other variables"
                )
            _node[path[-1]] = value
        return _env

    def _init_from_file(self, file_name: str) -> dict[str, dict[str, Any]]:
        try:
            return self._files.read_yaml(self._paths.env_path(file_name))
        except FileNotFoundError:
            return {}


class EnvironmentSection(Protocol):
    def __init__(self) -> None:
        pass


EnvT = TypeVar("EnvT", bound=EnvironmentSection)


def environment(name: str, *, cache: Cache | None = None) -> Callable[[type[EnvT]], type[EnvT]]:
    def decorator(cls: type[EnvT]) -> type[EnvT]:
        meta.set(cls, _EnvSectionMeta(name))
        (cache or __user_cache__).add(EnvironmentSection, cls)
        return cls

    return decorator


class CoreSection:
    debug: bool = False

    @init_method
    def _init_debug(self, cache: Cache) -> None:
        cache.debug = self.debug
