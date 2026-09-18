import dataclasses
from collections.abc import Mapping
from typing import Any, override

from peritype import TWrap

from bolinette.core.mapping._absence import ABSENT, Maybe
from bolinette.core.mapping._protocol import ObjectProtocol
from bolinette.core.mapping._spec import FieldSpec
from bolinette.core.mapping._utils import main_class


class DataclassProtocol(ObjectProtocol):
    priority = 70

    @override
    def matches(self, t: TWrap[Any]) -> bool:
        cls = main_class(t)
        return cls is not None and dataclasses.is_dataclass(cls)

    @override
    def fields(self, t: TWrap[Any]) -> dict[str, FieldSpec]:
        cls = main_class(t)
        if cls is None or not dataclasses.is_dataclass(cls):
            return {}
        hints = t.attribute_hints
        specs: dict[str, FieldSpec] = {}
        for f in dataclasses.fields(cls):
            has_default = f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
            specs[f.name] = FieldSpec.from_type(f.name, hints.get(f.name, f.type), has_default=has_default)
        return specs

    @override
    def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
        return getattr(obj, spec.key, ABSENT)

    @override
    def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
        cls = main_class(t)
        if cls is None or not dataclasses.is_dataclass(cls):
            raise TypeError(f"{t} is not a dataclass")
        init_names = {f.name for f in dataclasses.fields(cls) if f.init}
        init_kwargs = {k: v for k, v in values.items() if k in init_names}
        instance = cls(**init_kwargs)
        for k, v in values.items():
            if k not in init_names:
                setattr(instance, k, v)
        return instance
