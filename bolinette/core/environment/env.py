import os
from pathlib import Path
from typing import Any

import yaml

from bolinette.core import Cache, Logger, meta
from bolinette.core.environment.sections import EnvironmentSection, EnvSectionMeta
from bolinette.core.exceptions import EnvironmentError
from bolinette.core.expressions import ExpressionTree
from bolinette.core.injection import Injection, init_method
from bolinette.core.mapping import Mapper
from bolinette.core.types import Type


class Environment:
    _OS_ENV_PREFIX = "BLNT_"

    def __init__(self, cache: Cache, inject: Injection, logger: "Logger[Environment]") -> None:
        self._cache = cache
        self._inject = inject
        self._logger = logger
        self._env_folder = Path.cwd() / "env"
        self.profile: str
        self.config: dict[str, Any] = {}

    @init_method
    def init_profile(self) -> None:
        def read_profile() -> str:
            try:
                with open(self._env_folder / ".profile") as f:
                    for line in f:
                        return line.strip(" \n")
            except FileNotFoundError:
                self._logger.warning(".profile not found in env folder, defaulting to 'development'")
            return "development"

        self.profile = read_profile()

    @init_method
    def init(self) -> None:
        if EnvironmentSection in self._cache:
            for cls in self._cache.get(EnvironmentSection, hint=type[Any]):
                self._inject.add(cls, "singleton", before_init=[init_section])

        stack = [
            self._init_from_os(),
            self._init_from_file("env.yaml"),
            self._init_from_file(f"env.{self.profile}.yaml"),
            self._init_from_file(f"env.local.{self.profile}.yaml"),
        ]

        merged: dict[str, Any] = {}
        for node in stack:
            for name, section in node.items():
                if name not in merged:
                    merged[name] = {}
                for key, value in section.items():
                    merged[name][key] = value
        self.config = merged

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
            with open(self._env_folder / file_name) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}


def init_section(section: object, env: Environment, mapper: Mapper) -> None:
    section_name = meta.get(type(section), EnvSectionMeta).name
    if section_name not in env.config:
        raise EnvironmentError(f"No '{section_name}' section was found in the environment files")
    mapper.map(
        dict[str, Any],
        type(section),
        env.config[section_name],
        section,
        src_expr=ExpressionTree.new(Type(Environment))[section_name],
    )
