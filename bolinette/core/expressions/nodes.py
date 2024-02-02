from collections.abc import Iterable
from typing import Any, override

from bolinette.core import expressions
from bolinette.core.expressions.exceptions import ExpressionError
from bolinette.core.types import Type


class ExpressionNode:
    @override
    def __getattribute__(self, __name: str) -> Any:
        if __name == "__class__":
            return object.__getattribute__(self, "__class__")
        if __name == "__dict__":
            return object.__getattribute__(self, "__dict__")
        if __name == "__str__":
            return object.__getattribute__(self, "__str__")
        if __name == "__repr__":
            return object.__getattribute__(self, "__repr__")
        return AttributeNode(self, __name)

    def __getitem__(self, key: Any) -> "ElementNode[Any]":
        return ElementNode(self, key)

    def __expr_get_value__(self, obj: object) -> Any:
        raise ExpressionError(self, f"Cannot get value from {type(self).__name__}")

    def __expr_set_value__(self, obj: object, value: Any) -> None:
        raise ExpressionError(self, f"Cannot set value of {type(self).__name__}")

    def __expr_get_attribute__(self) -> str:
        raise ExpressionError(self, f"Cannot get attribute name of {type(self).__name__}")

    def __expr_format__(self, depth: int | None) -> str:
        raise ExpressionError(self, f"Cannot format {type(self).__name__}")

    def __expr_get_parents__(self) -> "Iterable[ExpressionNode]":
        raise ExpressionError(self, f"Cannot get parents from {type(self).__name__}")

    @override
    def __str__(self) -> str:
        return expressions.ExpressionTree.format(self)

    @override
    def __repr__(self) -> str:
        return f"<{type(self).__qualname__}: {expressions.ExpressionTree.format(self)}>"


class RootNode(ExpressionNode):
    def __init__(self, origin: Type[Any] | None = None) -> None:
        self.origin = origin

    @override
    def __expr_get_value__(self, obj: object) -> Any:
        return obj

    @override
    def __expr_format__(self, depth: int | None) -> str:
        if depth is not None and depth <= 0:
            return ""
        origin = object.__getattribute__(self, "origin")
        if origin is None:
            return "$"
        return str(origin)

    @override
    def __expr_get_parents__(self) -> Iterable[ExpressionNode]:
        return []


class ChildNode(ExpressionNode):
    def __init__(self, parent: ExpressionNode) -> None:
        self.parent = parent

    @override
    def __expr_get_parents__(self) -> Iterable[ExpressionNode]:
        parent = object.__getattribute__(self, "parent")
        return [parent]


class AttributeNode(ChildNode):
    def __init__(self, parent: ExpressionNode, attr: str) -> None:
        ChildNode.__init__(self, parent)
        self.attr = attr

    @override
    def __expr_get_value__(self, obj: object) -> Any:
        parent = object.__getattribute__(self, "parent")
        attr = object.__getattribute__(self, "attr")
        return getattr(expressions.ExpressionTree.get_value(parent, obj), attr)

    @override
    def __expr_set_value__(self, obj: object, value: Any) -> None:
        parent = object.__getattribute__(self, "parent")
        attr = object.__getattribute__(self, "attr")
        setattr(expressions.ExpressionTree.get_value(parent, obj), attr, value)

    @override
    def __expr_get_attribute__(self) -> str:
        return object.__getattribute__(self, "attr")

    @override
    def __expr_format__(self, depth: int | None) -> str:
        attr = object.__getattribute__(self, "attr")
        if depth is not None:
            if depth <= 1:
                return f"{attr}"
            depth -= 1
        parent = object.__getattribute__(self, "parent")
        return f"{expressions.ExpressionTree.format(parent, max_depth=depth)}.{attr}"


class ElementNode[K](ChildNode):
    def __init__(self, parent: ExpressionNode, key: K) -> None:
        ChildNode.__init__(self, parent)
        self.key = key

    @override
    def __expr_get_value__(self, obj: object) -> Any:
        parent = object.__getattribute__(self, "parent")
        key = object.__getattribute__(self, "key")
        return expressions.ExpressionTree.get_value(parent, obj)[key]

    @override
    def __expr_set_value__(self, obj: object, value: Any) -> None:
        parent = object.__getattribute__(self, "parent")
        key = object.__getattribute__(self, "key")
        expressions.ExpressionTree.get_value(parent, obj)[key] = value

    @override
    def __expr_get_attribute__(self) -> str:
        return object.__getattribute__(self, "key")

    @override
    def __expr_format__(self, depth: int | None) -> str:
        key = object.__getattribute__(self, "key")
        if isinstance(key, str):
            key_s = f"'{key}'"
        else:
            key_s = str(key)
        if depth is not None:
            if depth <= 1:
                return f"[{key_s}]"
            depth -= 1
        parent = object.__getattribute__(self, "parent")
        return f"{expressions.ExpressionTree.format(parent, max_depth=depth)}[{key_s}]"
