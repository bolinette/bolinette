from typing import Any, cast

from peritype import wrap_type

from bolinette.core.expressions import ExpressionNode
from bolinette.core.expressions._nodes import AttributeNode, ElementNode, RootNode
from bolinette.core.mapping._absence import ABSENT, Maybe, is_present
from bolinette.core.mapping._protocol import ProtocolRegistry


def _chain(expr: ExpressionNode) -> list[ExpressionNode]:
    steps: list[ExpressionNode] = []
    node = expr
    while True:
        cls = object.__getattribute__(node, "__class__")
        if cls is RootNode:
            break
        if cls not in (AttributeNode, ElementNode):
            raise TypeError(f"Cannot evaluate expression '{expr}': only attribute and item access are supported")
        steps.append(node)
        node = object.__getattribute__(node, "parent")
    steps.reverse()
    return steps


def read_expr(expr: ExpressionNode, obj: Any, registry: ProtocolRegistry) -> Maybe[Any]:
    current: Any = obj
    for step in _chain(expr):
        if current is None:
            return ABSENT
        if object.__getattribute__(step, "__class__") is ElementNode:
            key = object.__getattribute__(step, "key")
            try:
                current = current[key]
            except (KeyError, IndexError, TypeError):
                return ABSENT
            continue
        attr: str = object.__getattribute__(step, "attr")
        protocol = registry.resolve(wrap_type(cast(type[Any], type(current))))
        spec = protocol.fields(wrap_type(cast(type[Any], type(current)))).get(attr) if protocol is not None else None
        if protocol is not None and spec is not None:
            value = protocol.read_field(current, spec)
        else:
            value = getattr(current, attr, ABSENT)
        if not is_present(value):
            return ABSENT
        current = value
    return current
