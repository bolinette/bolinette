import typing
from collections.abc import Mapping
from typing import Any, override

from peritype import TWrap

from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping._absence import ABSENT, Maybe
from bolinette.core.mapping._protocol import ObjectProtocol
from bolinette.core.mapping._spec import FieldSpec
from bolinette.core.mapping._utils import main_class


class TypedDictProtocol(ObjectProtocol):
    priority = 80

    @override
    def matches(self, t: TWrap[Any]) -> bool:
        cls = main_class(t)
        return cls is not None and typing.is_typeddict(cls)

    @override
    def fields(self, t: TWrap[Any]) -> dict[str, FieldSpec]:
        cls = main_class(t)
        if cls is None:
            return {}
        optional: frozenset[str] = getattr(cls, "__optional_keys__", frozenset())
        return {
            key: FieldSpec.from_type(key, hint, has_default=key in optional) for key, hint in t.attribute_hints.items()
        }

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
