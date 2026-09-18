import inspect
from collections.abc import Mapping
from typing import Any, override

from peritype import TWrap
from peritype.errors import UnresolvedForwardRefError, UnresolvedTypeVarError

from bolinette.core.mapping._absence import ABSENT, Maybe
from bolinette.core.mapping._protocol import ObjectProtocol
from bolinette.core.mapping._spec import FieldSpec
from bolinette.core.mapping._utils import main_class
from bolinette.core.mapping.exceptions import InstantiationError


class PlainObjectProtocol(ObjectProtocol):
    priority = 0

    @override
    def matches(self, t: TWrap[Any]) -> bool:
        return main_class(t) is not None

    @override
    def fields(self, t: TWrap[Any]) -> dict[str, FieldSpec]:
        cls = main_class(t)
        if cls is None:
            return {}
        try:
            hints = t.attribute_hints
        except (UnresolvedForwardRefError, UnresolvedTypeVarError, TypeError):
            hints = {}
        return {
            key: FieldSpec.from_type(key, hint, has_default=self._has_real_default(cls, key))
            for key, hint in hints.items()
            if not key.startswith("__")
        }

    @staticmethod
    def _has_real_default(owner: type[Any], key: str) -> bool:
        for klass in owner.__mro__:
            if key in vars(klass):
                value = vars(klass)[key]

                return not (inspect.isdatadescriptor(value) or inspect.isroutine(value))
        return False

    @override
    def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
        return getattr(obj, spec.key, ABSENT)

    @override
    def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
        cls = main_class(t)
        if cls is None:
            raise InstantiationError(f"Could not instantiate {t}")
        params: Mapping[str, inspect.Parameter]
        try:
            params = inspect.signature(cls).parameters
        except (ValueError, TypeError):
            params = {}
        init_kwargs: dict[str, Any] = {}
        for name, param in params.items():
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            if name in values:
                init_kwargs[name] = values[name]
        try:
            instance = cls(**init_kwargs)
        except Exception as err:
            raise InstantiationError(f"Could not instantiate {t}") from err
        for key, value in values.items():
            if key not in init_kwargs:
                setattr(instance, key, value)
        return instance
