import inspect
from collections.abc import Callable
from typing import Any, Generic, ParamSpec, TypeVar

from bolinette.core import Cache
from bolinette.core.cache import P
from bolinette.core.exceptions import (
    AnnotationMissingInjectionError,
    InstanceExistsInjectionError,
    InvalidArgCountInjectionError,
    NoLiteralMatchInjectionError,
    NoPositionalParameterInjectionError,
    TooManyLiteralMatchInjectionError,
    TypeNotRegisteredInjectionError,
    TypeRegisteredInjectionError,
)

P_Func = ParamSpec("P_Func")
T_Func = TypeVar("T_Func")
T_Instance = TypeVar("T_Instance")


class _RegisteredType(Generic[T_Instance]):
    """
    **For internal use only**

    Holds informations about a type registered in the injection
    system and its instance after it has been initialized.
    """

    def __init__(
        self,
        inject: "Injection",
        cls: type[T_Instance],
        instance: T_Instance | None = None,
        func: Callable[[T_Instance], None] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        self.inject = inject
        self.type = cls
        self.instance = instance
        self.func = func
        self.params = params

    def instanciate(self, args: dict[str, Any]) -> T_Instance:
        self.instance = self.type(**args)
        if self.func is not None:
            self.inject.call(self.func, args=[self.instance])
        return self.instance


class Injection:
    """
    Bolinette's injection system.

    It is used to instanciate all services and call any function that use inversion of control.

    This system is the foundation of Bolinette and is used internally across all extensions.
    It can also be used to call any type or function to easily inject parameters without having
    to require each one at a time.
    """

    def __init__(self, cache: Cache) -> None:
        self._cache = cache
        self._types: dict[type[Any], _RegisteredType[Any]] = {}
        self._names: dict[str, type[Any]] = {}
        self.add(Injection, self)
        self._init_from_cache()

    def _init_from_cache(self) -> None:
        """Collects all types from the cache."""
        for t in self._cache.types:
            self.add(t)

    def _find_type_by_name(
        self, func: Callable, param: str, name: str
    ) -> type[Any] | None:
        """
        Looks for all the registered types which end match the given name.

        Raises if none or more than one match is found.
        """
        names = [n for n in self._names if n.endswith(name)]
        if not names:
            raise NoLiteralMatchInjectionError(func, param, name)
        if (l := len(names)) > 1:
            raise TooManyLiteralMatchInjectionError(func, param, name, l)
        return self._names[names[0]]

    def _resolve_args(
        self,
        func: Callable[P_Func, T_Func],
        immediate: bool,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Tries to map every parameter of the callable and raises if it fails.

        Parameters are looked up from the given kwargs overrides then from the injection registry.
        When resolving for a class `__init__` function (with the require method), non-instanciated types will
        be injected with a `_ProxyHook`. That hook will later be replaced with a lazy property that instanciates
        the type only on the first call.
        """

        params = dict(inspect.signature(func).parameters)
        if any(
            (n, p)
            for n, p in params.items()
            if p.kind in [p.POSITIONAL_ONLY, p.VAR_POSITIONAL]
        ):
            raise NoPositionalParameterInjectionError(func)

        f_args: dict[str, Any] = {}
        _args = [*args]
        _kwargs = {**kwargs}

        # Iterating over the parameters of the callable
        for p_name, param in params.items():
            if param.kind == param.VAR_KEYWORD:
                for kw_name, kw_value in _kwargs.items():
                    f_args[kw_name] = kw_value
                _kwargs = {}
                break

            # Looking for parameters in the args and kwargs
            if _args:
                f_args[p_name] = _args.pop(0)
            elif p_name in _kwargs:
                f_args[p_name] = _kwargs.pop(p_name)
            elif param.default is not param.empty:
                f_args[p_name] = param.default
            else:
                # No params were found in the kwargs, try to find them in the registry
                hint = param.annotation
                if hint == inspect.Signature.empty:
                    raise AnnotationMissingInjectionError(func, p_name)
                elif isinstance(hint, type) or isinstance(hint, str):
                    cls: type[Any] | None = None
                    if isinstance(hint, str):
                        cls = self._find_type_by_name(func, p_name, hint)
                    else:
                        cls = hint
                    if cls is not None:
                        if cls not in self._types:
                            raise TypeNotRegisteredInjectionError(cls)
                        else:
                            r_type = self._types[cls]
                            if r_type.instance is None:
                                if immediate:
                                    f_args[p_name] = self._instanciate(r_type)
                                else:
                                    f_args[p_name] = _ProxyHook(r_type)
                            else:
                                f_args[p_name] = r_type.instance

        if (_args or _kwargs):
            raise InvalidArgCountInjectionError(func, len(params), len(args) + len(kwargs))

        return f_args

    def _hook_proxies(self, instance: Any) -> None:
        """Replaces injection hooks with injection proxies"""
        cls = type(instance)
        attrs = dict(vars(instance))
        for name, attr in attrs.items():
            if isinstance(attr, _ProxyHook):
                delattr(instance, name)
                setattr(cls, name, _InjectionProxy(self, name, attr.type))

    def _instanciate(
        self,
        r_type: _RegisteredType[T_Instance],
        *,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> T_Instance:
        """
        Creates the instance for a registered type only once.

        After calling the constructor, all `_ProxyHook`s are replaced with `_InjectionProxy`s
        """
        if r_type.instance is not None:
            raise InstanceExistsInjectionError(r_type.type)
        func_args = self._resolve_args(r_type.type, False, args or [], kwargs or {})
        instance = r_type.instanciate(func_args)
        self._hook_proxies(instance)
        return instance

    def call(
        self,
        func: Callable[P_Func, T_Func],
        *,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> T_Func:
        """
        Uses the injection system to call the given function.

        `args` and `kwargs` are used first and the missing parameters are picked from the registry.
        Any undetermined parameter remaining will raise an `InjectionError`
        """
        func_args = self._resolve_args(func, True, args or [], kwargs or {})
        return func(**func_args)

    def add(
        self,
        cls: type[T_Instance],
        instance: T_Instance | None = None,
        func: Callable[[T_Instance], None] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        """
        Adds a type to the injection registry.

        - The `instance` can be provided and will be used during injection.
        - `func` will be called after the initialization.
          If an instance is given, `func` will never be called.
        - `params` are additional parameters that will be used during instanciation.
          These are keyword based.
        """
        if cls in self._types:
            raise TypeRegisteredInjectionError(cls)
        self._types[cls] = _RegisteredType(self, cls, instance, func, params)
        self._names[f"{cls.__module__}.{cls.__name__}"] = cls

    def require(self, cls: type[T_Instance]) -> T_Instance:
        """
        Returns the instance of the registered type.
        """
        if cls not in self._types:
            raise TypeNotRegisteredInjectionError(cls)
        _r_type = self._types[cls]
        if _r_type.instance is None:
            return self._instanciate(_r_type)
        return _r_type.instance


class _ProxyHook:
    """Temporary object used to locate injected types after assignements in the `__init__` function of an instance"""

    def __init__(self, r_type: _RegisteredType) -> None:
        self.type = r_type


class _InjectionProxy(Generic[T_Instance]):
    """
    Holds informations about a non-initialized type waiting for the first call.

    A proxy is attached to the class and acts like a built-in property.
    On the first call, it replaced itself with the wanted instance, instanciating it if needed.
    """

    def __init__(
        self, inject: Injection, name: str, cls: _RegisteredType[T_Instance]
    ) -> None:
        self._inject = inject
        self._name = name
        self._cls = cls

    def __get__(self, instance: Any, _) -> T_Instance:
        obj = self._cls.instance
        if obj is None:
            obj = self._inject._instanciate(self._cls)
        setattr(instance, self._name, obj)
        return obj
