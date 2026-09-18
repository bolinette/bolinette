import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from soupape import post_init

from bolinette.core import meta
from bolinette.core.configuration import ConfigSection
from bolinette.core.configuration._sections import ConfigSectionMeta
from bolinette.core.exceptions import ConfigurationError, InitError
from bolinette.core.mapping import BolinetteModel


@dataclass
class ConfigurationOptions:
    env_folder: Path | None = None


class Configuration:
    _OS_ENV_PREFIX = "BLNT_"
    _UNINITIALIZED_PROFILE = "__uninitialized__"
    _DEFAULT_PROFILE = "development"

    def __init__(self, options: ConfigurationOptions, base: "BaseConfiguration | None" = None) -> None:
        self._env_folder = options.env_folder if options.env_folder is not None else Path.cwd() / "env"
        self._base_config = base
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
    def _init_env_files(self) -> None:
        profile = self._DEFAULT_PROFILE if self.profile == self._UNINITIALIZED_PROFILE else self.profile

        stack = [
            self._base_config.config if self._base_config is not None else {},
            self._init_from_os(),
            self._init_from_file("env.toml"),
            self._init_from_file(f"env.{profile}.toml"),
            self._init_from_file(f"env.local.{profile}.toml"),
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

    @staticmethod
    def _init_from_os() -> dict[str, dict[str, Any]]:
        _vars: dict[str, str] = {}
        prefix_len = len(Configuration._OS_ENV_PREFIX)
        for var in os.environ:
            if var.startswith(Configuration._OS_ENV_PREFIX):
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
                raise ConfigurationError(
                    f"OS variable '{Configuration._OS_ENV_PREFIX}{key}' conflicts with other variables"
                )
            _node[path[-1]] = value
        return _env

    def _init_from_file(self, file_name: str) -> dict[str, dict[str, Any]]:
        try:
            with open(self._env_folder / file_name, "rb") as f:
                return tomllib.load(f)
        except FileNotFoundError:
            return {}


@dataclass
class BaseConfiguration:
    config: dict[str, dict[str, Any]]


def resolve_config_section[T: BolinetteModel](env: Configuration, section_type: type[T]) -> ConfigSection[T]:
    if not meta.has(section_type, ConfigSectionMeta.META_KEY):
        raise InitError(f"{section_type} is not a configuration section, decorate it with @config_section")
    section_meta: ConfigSectionMeta = meta.get(section_type, ConfigSectionMeta.META_KEY)
    return ConfigSection(
        section_type, section_meta.name, section_type.model_validate(env.config.get(section_meta.name, {}))
    )
