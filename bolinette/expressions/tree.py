from typing import Any
from abc import ABC

from bolinette.exceptions import ExpressionError


class ExpressionNode(ABC):
    def __getattribute__(self, __name: str) -> "AttributeNode":
        return AttributeNode(self, __name)


class RootNode(ExpressionNode):
    pass


class AttributeNode(ExpressionNode):
    def __init__(self, parent: ExpressionNode, attr: str) -> None:
        self.parent = parent
        self.attr = attr


class ExpressionTree:
    def __init__(self) -> None:
        raise TypeError(f"Cannot instanciate {ExpressionTree}")

    @staticmethod
    def new() -> RootNode:
        return RootNode()

    @staticmethod
    def get_value(expr: ExpressionNode, obj: object) -> Any:
        cls = type(expr)
        if cls is RootNode:
            return obj
        if cls is AttributeNode:
            parent = object.__getattribute__(expr, "parent")
            attr = object.__getattribute__(expr, "attr")
            return getattr(ExpressionTree.get_value(parent, obj), attr)
        raise ValueError()

    @staticmethod
    def set_value(expr: ExpressionNode, obj: object, value: Any) -> None:
        cls = type(expr)
        if cls is RootNode:
            raise ExpressionError("Cannot set value of root expression node")
        if cls is AttributeNode:
            parent = object.__getattribute__(expr, "parent")
            attr = object.__getattribute__(expr, "attr")
            setattr(ExpressionTree.get_value(parent, obj), attr, value)
            return
        raise ValueError()

    @staticmethod
    def get_attribute_name(expr: AttributeNode) -> str:
        return object.__getattribute__(expr, "attr")
