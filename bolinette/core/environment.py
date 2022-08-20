import inspect
import os
from collections.abc import Callable
from types import UnionType
from typing import Any, Protocol, TypeVar, Union, get_args, get_origin

from bolinette.core import (
    Cache,
    CoreSection,
    Injection,
    Logger,
    __core_cache__,
    init_method,
    meta,
)
from bolinette.core.exceptions import EnvironmentError, InitError
from bolinette.core.utils import FileUtils, PathUtils

_NoAnnotation = type("_NoAnnotation", (), {})


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
        if EnvironmentSection in self._cache:
            for cls in self._cache[EnvironmentSection, type]:
                self._inject.add(cls, "singleton", init_methods=[self._init_section])

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
                if isinstance(section, str):
                    raise AttributeError(section, node, stack)
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


class EnvironmentSection(Protocol):
    def __init__(self) -> None:
        pass


EnvT = TypeVar("EnvT", bound=EnvironmentSection)


def environment(
    name: str, *, cache: Cache | None = None
) -> Callable[[type[EnvT]], type[EnvT]]:
    def decorator(cls: type[EnvT]) -> type[EnvT]:
        meta.set(cls, _EnvSectionMeta(name))
        (cache or __core_cache__).add(EnvironmentSection, cls)
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

    def _parse_object(self, obj: object, node: dict[str, Any], path: str) -> None:
        for att_name, annotation in obj.__annotations__.items():
            sub_path = f"{path}.{att_name}"
            default_set = False
            default = None
            if hasattr(obj, att_name):
                default_set = True
                default = getattr(obj, att_name)
            env_value = _EnvParser._get_value(
                path, att_name, node, default_set, default
            )
            value = self._parse_value(annotation, env_value, sub_path)
            setattr(obj, att_name, value)

    def _parse_value(self, annotation: Any, value: Any, path: str) -> Any:
        if annotation in (_NoAnnotation, Any):
            return value
        if isinstance(annotation, str):
            raise EnvironmentError(f"Section {path}: no literal allowed in type hints")
        nullable = False
        if origin := get_origin(annotation):
            type_args = get_args(annotation)
            if origin in (UnionType, Union):
                nullable = type(None) in type_args
                if (nullable and len(type_args) >= 3) or not nullable:
                    raise EnvironmentError(
                        f"Section {path}: type unions are not allowed"
                    )
                annotation = next(filter(lambda t: t is not type(None), type_args))
            elif origin is list:
                return self._parse_list(value, type_args[0], path)
            else:
                raise EnvironmentError(
                    f"Section {path}: unsupported generic type {origin}"
                )
        if value is None:
            if not nullable:
                raise EnvironmentError(
                    f"Section {path}: attemting to bind None value to a non-nullable attribute"
                )
            value = None
        elif annotation is list:
            return self._parse_list(value, _NoAnnotation, path)
        elif annotation in (str, int, float, bool):
            try:
                value = annotation(value)
            except (ValueError):
                raise EnvironmentError(
                    f"Section {path}: unable to bind value {value} to type {annotation}"
                )
        elif isinstance(annotation, type):
            if len(inspect.signature(annotation).parameters) != 0:
                raise EnvironmentError(
                    f"Section {annotation} must have an empty __init__ method"
                )
            if not isinstance(value, dict):
                raise EnvironmentError(
                    f"Section {path} is typed has a class and can only be mapped from a dictionnary"
                )
            sub_obj = annotation()
            self._parse_object(sub_obj, value, path)
            value = sub_obj
        else:
            raise EnvironmentError(
                f"Unable to bind value to section {path}, "
                "be sure to type hint with only classes and buit-in types"
            )
        return value

    def _parse_list(self, value: Any, arg_type: type | None, path: str) -> list[Any]:
        if not isinstance(value, list):
            raise EnvironmentError(
                f"Section {path} must be binded to a list, {type(value)} found"
            )
        index = 0
        l = []
        for elem in value:
            sub_path = f"{path}[{index}]"
            l.append(self._parse_value(arg_type, elem, sub_path))
            index += 1
        return l

    def parse(self) -> None:
        self._parse_object(self._object, self._env, str(type(self._object)))


environment("core")(CoreSection)
