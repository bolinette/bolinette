from typing import Any

from bolinette.core.expressions.exceptions import AttributeChainError, MaxDepthExpressionError
from bolinette.core.expressions.nodes import AttributeNode, ElementNode, ExpressionNode, RootNode
from bolinette.core.types import Type


class ExpressionTree:
    def __init__(self) -> None:
        raise TypeError(f"Cannot instantiate {ExpressionTree}")

    @staticmethod
    def new(origin: Type[Any] | None = None) -> RootNode:
        return RootNode(origin)

    @staticmethod
    def get_value(expr: ExpressionNode, obj: object) -> Any:
        return object.__getattribute__(expr, "__expr_get_value__")(obj)

    @staticmethod
    def set_value(expr: ExpressionNode, obj: object, value: Any) -> None:
        return object.__getattribute__(expr, "__expr_get_value__")(obj, value)

    @staticmethod
    def get_attribute(expr: ExpressionNode) -> str:
        return object.__getattribute__(expr, "__expr_get_attribute__")()

    @staticmethod
    def format(expr: ExpressionNode, *, max_depth: int | None = None) -> str:
        return object.__getattribute__(expr, "__expr_format__")(max_depth)

    @staticmethod
    def ensure_attribute_chain(
        expr: ExpressionNode,
        *,
        max_depth: int | None = None,
        origin: ExpressionNode | None = None,
    ) -> None:
        if max_depth is not None:
            if max_depth == 0:
                if object.__getattribute__(expr, "__class__") != RootNode:
                    raise MaxDepthExpressionError(origin or expr)
            elif object.__getattribute__(expr, "__class__") not in (AttributeNode, ElementNode):
                raise AttributeChainError(origin or expr)
        parents: list[ExpressionNode] = object.__getattribute__(expr, "__expr_get_parents__")()
        for parent in parents:
            ExpressionTree.ensure_attribute_chain(
                parent,
                max_depth=max_depth - 1 if max_depth is not None else None,
                origin=origin or expr,
            )
