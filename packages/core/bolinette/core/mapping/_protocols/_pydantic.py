from collections.abc import Mapping
from typing import Any, override

from peritype import TWrap
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from bolinette.core.mapping._absence import ABSENT, Maybe
from bolinette.core.mapping._protocol import ObjectProtocol
from bolinette.core.mapping._spec import FieldSpec
from bolinette.core.mapping._utils import main_class


class PydanticProtocol(ObjectProtocol):
    priority = 90

    @override
    def matches(self, t: TWrap[Any]) -> bool:
        cls = main_class(t)
        return cls is not None and issubclass(cls, BaseModel)

    @override
    def fields(self, t: TWrap[Any]) -> dict[str, FieldSpec]:
        cls = main_class(t)
        if cls is None or not issubclass(cls, BaseModel):
            return {}
        specs: dict[str, FieldSpec] = {}
        for key, info in cls.model_fields.items():
            has_default = info.default is not PydanticUndefined or info.default_factory is not None
            specs[key] = FieldSpec.from_type(key, info.annotation, has_default=has_default)
        return specs

    @override
    def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
        if not isinstance(obj, BaseModel):
            return ABSENT

        if spec.key not in obj.model_fields_set:
            return ABSENT
        return getattr(obj, spec.key, ABSENT)

    @override
    def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
        cls = main_class(t)
        if cls is None:
            raise TypeError(f"{t} is not a pydantic model")
        return cls(**values)
