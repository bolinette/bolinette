from collections.abc import Mapping
from typing import Any, override

from peritype import TWrap

from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping._absence import ABSENT, Maybe
from bolinette.core.mapping._protocol import ObjectProtocol
from bolinette.core.mapping._spec import FieldSpec
from bolinette.core.mapping._utils import dict_value_type, main_class


class MappingProtocol(ObjectProtocol):
    priority = 20
    knows_fields = False

    @override
    def matches(self, t: TWrap[Any]) -> bool:
        cls = main_class(t)
        return cls is not None and issubclass(cls, dict)

    @override
    def fields(self, t: TWrap[Any]) -> dict[str, FieldSpec]:
        return {}

    @override
    def value_type(self, t: TWrap[Any]) -> TWrap[Any]:
        return dict_value_type(t)

    @override
    def instance_fields(self, obj: Any, t: TWrap[Any]) -> dict[str, FieldSpec]:
        if not isinstance(obj, dict):
            return {}
        value_t = self.value_type(t)
        return {str(key): FieldSpec.from_type(str(key), value_t) for key in obj}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]

    @override
    def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
        if not isinstance(obj, dict):
            return ABSENT
        return obj.get(spec.key, ABSENT)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    @override
    def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
        return dict(values)

    @override
    def assign(self, obj: Any, spec: FieldSpec, value: Any) -> None:
        obj[spec.key] = value

    @override
    def child_path(self, expr: ExpressionNode, key: str) -> ExpressionNode:
        return expr[key]
