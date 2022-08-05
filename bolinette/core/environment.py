import inspect
import os
from collections.abc import Callable
from types import UnionType
from typing import Any, TypeVar, Union, get_args, get_origin

from bolinette.core import (
    Cache,
    CoreSection,
    Injection,
    InjectionStrategy,
    Logger,
    __core_cache__,
    init_method,
    meta,
)
from bolinette.core.exceptions import EnvironmentError, InitError
from bolinette.core.utils import FileUtils, PathUtils

T = TypeVar("T")


class _EnvSectionMeta:
    def __init__(self, name: str) -> None:
        self.name = name


class Environment:
    _OS_ENV_PREFIX = "BLNT_"

    def __init__(
        self,
        profile: str,
        logger: Logger,
        cache: Cache,
        inject: Injection,
        paths: PathUtils,
        files: FileUtils,
        *,
        env_path: str = "env",
    ) -> None:
        self._profile = profile
        self._logger = logger
        self._cache = cache
        self._inject = inject
        self._paths = paths
        self._files = files
        self._path = env_path
        self._raw_env: dict[str, Any] = {}

    def _init_section(self, section: object) -> None:
        section_name = meta.get(type(section), _EnvSectionMeta).name
        if section_name not in self._raw_env:
            raise EnvironmentError(
                f"No '{section_name}' section was found in the environment files"
            )
        _EnvParser(self._raw_env[section_name], section).parse()

    @init_method
    def init(self) -> None:
        for name, cls in self._cache.env_sections:
            if len(inspect.signature(cls).parameters) != 0:
                raise InitError(f"Section {cls} must have an empty __init__ method")
            meta.set(cls, _EnvSectionMeta(name))
            self._inject.add(
                cls, InjectionStrategy.Singleton, init_methods=[self._init_section]
            )

        stack = [
            self._init_from_os(),
            self._init_from_file("env.yaml"),
            self._init_from_file(f"env.{self._profile}.yaml"),
            self._init_from_file(f"env.local.{self._profile}.yaml"),
        ]

        merged: dict = {}
        for node in stack:
            for name, section in node.items():
                if name not in merged:
                    merged[name] = {}
                for key, value in section.items():
                    merged[name][key] = value
        self._raw_env = merged

        if self._inject.is_registered(CoreSection):
            self._cache.debug = self._inject.require(CoreSection).debug

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


def environment(
    name: str, *, cache: Cache | None = None
) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        if not inspect.isclass(cls):
            raise InitError(
                f"{cls} must be a class to be decorated with @{environment.__name__}"
            )
        (cache or __core_cache__).add_env_section(name, cls)
        return cls

    return decorator


class _EnvParser:
    def __init__(self, env: dict[str, Any], obj: object) -> None:
        self._env = env
        self._object = obj

    @staticmethod
    def _get_value(
        path: str,
        name: str,
        node: dict[str, Any],
        default_set: bool,
        default: Any,
    ) -> Any:
        if name not in node:
            if not default_set:
                raise EnvironmentError(
                    f"Section {path}: "
                    "no value to bind found in environment and no default value set"
                )
            return default
        return node[name]

    @staticmethod
    def _parse_object(obj: object, node: dict[str, Any], path: str) -> None:
        for att_name, annotation in obj.__annotations__.items():
            sub_path = f"{path}.{att_name}"
            if isinstance(annotation, str):
                raise EnvironmentError(
                    f"Section {sub_path}: no literal allowed in type hints"
                )
            nullable = False
            if get_origin(annotation) in [UnionType, Union]:
                type_args = get_args(annotation)
                nullable = type(None) in type_args
                if (nullable and len(type_args) >= 3) or not nullable:
                    raise EnvironmentError(
                        f"Section {sub_path}: type unions are not allowed"
                    )
                annotation = next(filter(lambda t: t is not type(None), type_args))
            default_set = False
            default = None
            if hasattr(obj, att_name):
                default_set = True
                default = getattr(obj, att_name)
            value = _EnvParser._get_value(path, att_name, node, default_set, default)
            if value is None:
                if not nullable:
                    raise EnvironmentError(
                        f"Section {sub_path}: attemting to bind None value to a non-nullable attribute"
                    )
                value = None
            elif annotation in (str, int, float, bool):
                try:
                    value = annotation(value)
                except (ValueError):
                    raise EnvironmentError(
                        f"Section {sub_path}: unable to bind value {value} to type {annotation}"
                    )
            elif inspect.isclass(annotation):
                if len(inspect.signature(annotation).parameters) != 0:
                    raise EnvironmentError(
                        f"Section {annotation} must have an empty __init__ method"
                    )
                if not isinstance(value, dict):
                    raise EnvironmentError(
                        f"Section {sub_path} is typed has a class and can only be mapped from a dictionnary"
                    )
                sub_obj = annotation()
                _EnvParser._parse_object(sub_obj, value, sub_path)
                value = sub_obj
            else:
                raise EnvironmentError(
                    f"Unable to bind value to section {sub_path}, "
                    "be sure to type hint with only classes and buit-in types"
                )
            setattr(obj, att_name, value)

    def parse(self) -> None:
        self._parse_object(self._object, self._env, str(type(self._object)))


environment("core")(CoreSection)
