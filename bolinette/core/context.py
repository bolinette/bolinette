from abc import ABC
from typing import Any, TypeVar, overload

from bolinette import core
from bolinette.exceptions import InternalError
from bolinette.utils import files, paths


T_ExtCtx = TypeVar("T_ExtCtx", bound=core.ExtensionContext)


class AbstractContext(ABC):
    ...


class BolinetteContext(AbstractContext):
    def __init__(
        self, origin: str, *, profile: str = None, overrides: dict[str, Any] = None
    ):
        self._origin = origin
        self._cwd = paths.cwd()
        self.env = core.Environment(self, profile=profile, overrides=overrides)
        self.inject = core.BolinetteInjection(self)
        self.registry = InstanceRegistry()
        self.manifest = (
            files.read_manifest(
                self.root_path(), params={"version": self.env.get("version", "0.0.0")}
            )
            or {}
        )
        self.logger = core.Logger(self)
        self.jwt = core.JWT(self)

    def internal_path(self, *path):
        return paths.join(self._origin, *path)

    def internal_files_path(self, *path):
        return paths.join(self._origin, "_files", *path)

    def root_path(self, *path):
        return paths.join(self._cwd, *path)

    def instance_path(self, *path):
        return self.root_path("instance", *path)

    def env_path(self, *path):
        return self.root_path("env", *path)

    def static_path(self, *path):
        return self.root_path("static", *path)

    def templates_path(self, *path):
        return self.root_path("templates", *path)


class InstanceRegistry:
    def __init__(self) -> None:
        self._by_type: dict[type[Any], Any] = {}
        self._by_name: dict[str, Any] = {}

    @overload
    def get(self, _type: type[core.abc.T_Instance]) -> core.abc.T_Instance:
        ...

    @overload
    def get(self, name: str) -> Any:
        ...

    def get(self, param: type[Any] | str) -> Any:
        if isinstance(param, type):
            if param not in self._by_type:
                raise InternalError(
                    f"Injection error: No singleton of type {param} in context registry"
                )
            return self._by_type[param]
        if param in self._by_name:
            return self._by_name[param]
        match [n for n in self._by_name if param in n]:
            case matches if len(matches) > 1:
                raise InternalError(
                    f"Injection error: {len(matches)} matches found for {param} in context registry"
                )
            case matches if len(matches) > 0:
                return self._by_name[matches[0]]
        raise InternalError(
            f"Injection error: No match for {param} found in context registry"
        )

    @overload
    def __contains__(self, _type: type[Any]) -> bool:
        ...

    @overload
    def __contains__(self, name: str) -> bool:
        ...

    def __contains__(self, param: type[Any] | str) -> bool:
        if isinstance(param, type):
            return param in self._by_type
        match [n for n in self._by_name if param in n]:
            case matches if len(matches) > 1:
                raise InternalError(
                    f"Injection error: {len(matches)} matches found for {param} in context registry"
                )
            case matches if len(matches) > 0:
                return True
        return False

    def add(self, instance: Any):
        i_type: type = type(instance)
        self._by_type[i_type] = instance
        self._by_name[f"{i_type.__module__}.{i_type.__name__}"] = instance
