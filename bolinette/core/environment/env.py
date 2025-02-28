import os
import warnings
from pathlib import Path
from typing import Any

import yaml

from bolinette.core import Cache, meta
from bolinette.core.environment.sections import EnvironmentSection, EnvSectionMeta
from bolinette.core.exceptions import EnvironmentError
from bolinette.core.expressions import ExpressionTree
from bolinette.core.injection import Injection, post_init
from bolinette.core.mapping import Mapper
from bolinette.core.types import Type


class Environment:
    _OS_ENV_PREFIX = "BLNT_"
    _UNINITIALIZED_PROFILE = "__uninitialized__"
    _DEFAULT_PROFILE = "development"

    def __init__(self) -> None:
        self._env_folder = Path.cwd() / "env"
        self.profile: str = self._UNINITIALIZED_PROFILE
        self.config: dict[str, Any] = {}

    @post_init
    def _init_profile(self) -> None:
        try:
            with open(self._env_folder / ".profile") as f:
                for line in f:
                    self.profile = line.strip("\n")
                    break
        except FileNotFoundError:
            pass

    @post_init
    def _init_config_sections(self, cache: Cache, inject: Injection) -> None:
        if EnvironmentSection in cache:
            for cls in cache.get(EnvironmentSection, hint=type[Any]):
                inject.add_singleton(cls, options={"before_init": [init_section]})

    @post_init
    def _init_env_files(self) -> None:
        profile = self._DEFAULT_PROFILE if self.profile == self._UNINITIALIZED_PROFILE else self.profile

        stack = [
            self._init_from_os(),
            self._init_from_file("env.yaml"),
            self._init_from_file(f"env.{profile}.yaml"),
            self._init_from_file(f"env.local.{profile}.yaml"),
        ]

        merged: dict[str, Any] = {}
        for node in stack:
            for name, section in node.items():
                if name not in merged:
                    merged[name] = {}
                for key, value in section.items():
                    merged[name][key] = value
        self.config = merged

    @post_init
    def _init_default_profile(self) -> None:
        if self.profile == self._UNINITIALIZED_PROFILE:
            self.profile = self._DEFAULT_PROFILE
            warnings.warn(f".profile not found in env folder, defaulting to '{self._DEFAULT_PROFILE}'", stacklevel=1)

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
