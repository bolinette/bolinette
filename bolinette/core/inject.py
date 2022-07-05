from __future__ import annotations
import inspect
from collections.abc import Callable
from typing import Any, Generic, ParamSpec, TypeVar

from bolinette.core import __core_cache__, Cache
from bolinette.core.exceptions import InternalError

P_Func = ParamSpec("P_Func")
T_Func = TypeVar("T_Func")
T_Instance = TypeVar("T_Instance")


class InstantiableAttribute(Generic[T_Instance]):
    def __init__(self, _type: type[T_Instance], _dict: dict[str, Any]) -> None:
        self._type = _type
        self._dict = _dict

    @property
    def type(self):
        return self._type

    def pop(self, name: str) -> Any:
        if name not in self._dict:
            raise AttributeError(
                f"Instantiable attribute {self._type} has no {name} member"
            )
        return self._dict.pop(name)

    def instantiate(self, **kwargs) -> T_Instance:
        return self._type(**(self._dict | kwargs))


class _RegisteredType(Generic[T_Instance]):
    def __init__(
        self,
        _type: type[T_Instance],
        instance: T_Instance | None = None,
        func: Callable[[T_Instance], None] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        self.type = _type
        self.instance = instance
        self.func = func
        self.params = params

    def instanciate(self, args: dict[str, Any]) -> T_Instance:
        self.instance = self.type(**args)
        if self.func is not None:
            self.func(self.instance)
        return self.instance


class Injection:
    def __init__(self, *, cache: Cache | None = None) -> None:
        self._cache = cache if cache is not None else __core_cache__
        self._types: dict[type[Any], _RegisteredType[Any]] = {}
        self._names: dict[str, type[Any]] = {}
        self.add(Injection, self)
        self._init_from_cache()

    def _init_from_cache(self):
        for t in self._cache.types:
            self.add(t)

    def _find_type_by_name(self, name: str, errors: list[str]) -> type[Any] | None:
        names = [n for n in self._names if n.endswith(name)]
        if not names:
            errors.append(f"Literal '{name}' does not match any registered type")
            return None
        if (l := len(names)) > 1:
            errors.append(
                f"Literal '{name}' matches with {l} registered types, use a more explicit name"
            )
            return None
        return self._names[names[0]]

    def _resolve_args(
        self, func: Callable[P_Func, T_Func], *, immediate: bool
    ) -> dict[str, Any]:
        errors = []
        injected: dict[str, str | type] = {}
        params = inspect.signature(func).parameters
        for p_name, param in params.items():
            hint = param.annotation
            # If the annotation is a generic type
            if isinstance(getattr(hint, "__origin__", None), type):
                hint = hint.__origin__
            if hint == inspect.Signature.empty:
                errors.append(f"{p_name} param requires a type annotation")
            elif isinstance(hint, type) or isinstance(hint, str):
                injected[p_name] = hint
        f_args: dict[str, Any] = {}
        for p_name, _type in injected.items():
            _r_type: type[Any] | None = None
            if isinstance(_type, str):
                _r_type = self._find_type_by_name(_type, errors)
            else:
                _r_type = _type
            if _r_type is not None:
                if _r_type not in self._types:
                    errors.append(
                        f"{_r_type} is not a registered type in the injection system"
                    )
                else:
                    registered = self._types[_r_type]
                    if registered.instance is None:
                        if immediate:
                            f_args[p_name] = self.instanciate(registered)
                        else:
                            f_args[p_name] = _ProxyHook(registered)
                    else:
                        f_args[p_name] = registered.instance
        if len(errors) > 0:
            raise InternalError(
                f"Injection errors raised while attemping to call {func}:\n  "
                + "\n  Injection error: ".join(errors)
            )
        return f_args

    def _hook_proxies(self, instance: Any) -> None:
        _type = type(instance)
        attrs = dict(vars(instance))
        for name, attr in attrs.items():
            if isinstance(attr, _ProxyHook):
                delattr(instance, name)
                setattr(_type, name, _InjectionProxy(self, name, attr.type))

    def call(self, func: Callable[P_Func, T_Func]) -> T_Func:
        args = self._resolve_args(func, immediate=True)
        return func(**args)

    def add(
        self,
        _type: type[T_Instance],
        instance: T_Instance | None = None,
        func: Callable[[T_Instance], None] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        self._types[_type] = _RegisteredType(_type, instance, func, params)
        self._names[f"{_type.__module__}.{_type.__name__}"] = _type

    def require(self, _type: type[T_Instance]) -> T_Instance:
        if _type not in self._types:
            raise InternalError(
                f"{_type} is not a registered type in the injection system"
            )
        _r_type = self._types[_type]
        if _r_type.instance is None:
            return self.instanciate(_r_type)
        return _r_type.instance

    def instanciate(self, _type: _RegisteredType[T_Instance]) -> T_Instance:
        if _type.instance is not None:
            raise InternalError(f"'{_type.type}' has already been instanciated")
        args = self._resolve_args(_type.type, immediate=False)
        instance = _type.instanciate(args)
        self._hook_proxies(instance)
        return instance


class _ProxyHook:
    def __init__(self, _type: _RegisteredType) -> None:
        self.type = _type


class _InjectionProxy(Generic[T_Instance]):
    def __init__(
        self, inject: Injection, name: str, _type: _RegisteredType[T_Instance]
    ) -> None:
        self._inject = inject
        self._name = name
        self._type = _type

    def __get__(self, instance: Any, _) -> T_Instance:
        obj = self._type.instance
        if obj is None:
            obj = self._inject.instanciate(self._type)
        setattr(instance, self._name, obj)
        return obj
