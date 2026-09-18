"""Expression trees: lazily recorded attribute and item access paths."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.expressions._exceptions import AttributeChainError, ExpressionError, MaxDepthExpressionError
from bolinette.core.expressions._nodes import AttributeNode, ElementNode, RootNode


@dataclass
class Address:
    city: str


@dataclass
class Person:
    name: str
    address: Address
    tags: list[str] = field(default_factory=list[str])
    extra: dict[str, Any] = field(default_factory=dict[str, Any])


def _root() -> Any:
    return ExpressionTree.new()


class TestBuilding:
    def test_new_returns_a_root(self) -> None:
        """`new` creates a root node holding the optional origin."""
        root = ExpressionTree.new("origin")

        assert isinstance(root, RootNode)
        assert object.__getattribute__(root, "origin") == "origin"

    def test_attribute_access_records_a_node(self) -> None:
        """Accessing an attribute returns an `AttributeNode` instead of failing."""
        expr = _root().name

        assert isinstance(expr, AttributeNode)
        assert ExpressionTree.get_attribute(expr) == "name"

    def test_item_access_records_a_node(self) -> None:
        """Subscripting returns an `ElementNode` holding the key."""
        expr: ElementNode[str] = _root()["key"]

        assert isinstance(expr, ElementNode)
        assert ExpressionTree.get_attribute(expr) == "key"

    def test_cannot_instantiate_tree(self) -> None:
        """`ExpressionTree` is a namespace of static methods."""
        with pytest.raises(TypeError):
            ExpressionTree()


class TestFormat:
    def test_root_without_origin(self) -> None:
        """A root without origin formats as `$`."""
        assert str(ExpressionTree.new()) == "$"

    def test_root_with_origin(self) -> None:
        """A root with an origin formats as that origin."""
        assert str(ExpressionTree.new("Person")) == "Person"

    def test_chain(self) -> None:
        """Attribute and item nodes format as a dotted path with brackets."""
        expr = _root().address["city"][0]

        assert str(expr) == "$.address['city'][0]"

    def test_repr(self) -> None:
        """The representation names the node type and the formatted path."""
        assert repr(_root().name) == "<AttributeNode: $.name>"

    def test_max_depth(self) -> None:
        """`max_depth` keeps only the last steps of the path."""
        expr = _root().a.b.c

        assert ExpressionTree.format(expr, max_depth=1) == "c"
        assert ExpressionTree.format(expr, max_depth=2) == "b.c"
        assert ExpressionTree.format(_root()["k"].c, max_depth=2) == "['k'].c"


class TestEvaluation:
    def test_get_value(self) -> None:
        """`get_value` walks the recorded path on a real object."""
        person = Person("Bob", Address("Paris"), tags=["a", "b"], extra={"k": 1})

        assert ExpressionTree.get_value(_root().name, person) == "Bob"
        assert ExpressionTree.get_value(_root().address.city, person) == "Paris"
        assert ExpressionTree.get_value(_root().tags[1], person) == "b"
        assert ExpressionTree.get_value(_root().extra["k"], person) == 1

    def test_get_value_on_root(self) -> None:
        """The root evaluates to the object itself."""
        person = Person("Bob", Address("Paris"))

        assert ExpressionTree.get_value(ExpressionTree.new(), person) is person

    def test_set_value_on_attribute(self) -> None:
        """`set_value` assigns through the recorded attribute path."""
        person = Person("Bob", Address("Paris"))

        ExpressionTree.set_value(_root().address.city, person, "Lyon")

        assert person.address.city == "Lyon"

    def test_set_value_on_item(self) -> None:
        """`set_value` assigns through the recorded item path."""
        person = Person("Bob", Address("Paris"), tags=["a"])

        ExpressionTree.set_value(_root().tags[0], person, "z")

        assert person.tags == ["z"]

    def test_set_value_on_root_raises(self) -> None:
        """The root cannot be assigned."""
        with pytest.raises(ExpressionError):
            ExpressionTree.set_value(ExpressionTree.new(), object(), 1)

    def test_get_attribute_on_root_raises(self) -> None:
        """The root has no attribute name."""
        with pytest.raises(ExpressionError):
            ExpressionTree.get_attribute(ExpressionTree.new())


class TestAttributeChain:
    def test_valid_chain(self) -> None:
        """A chain of attribute and item nodes down to a root is accepted."""
        ExpressionTree.ensure_attribute_chain(_root().a["b"].c)

    def test_root_alone_is_accepted(self) -> None:
        """A bare root is a valid chain."""
        ExpressionTree.ensure_attribute_chain(ExpressionTree.new())

    def test_max_depth_accepts_exact_depth(self) -> None:
        """A chain of exactly `max_depth` steps is accepted."""
        ExpressionTree.ensure_attribute_chain(_root().a, max_depth=1)

    def test_max_depth_rejects_deeper_chain(self) -> None:
        """A chain longer than `max_depth` is rejected with the full expression in the message."""
        with pytest.raises(MaxDepthExpressionError, match=r"Expression \$\.a\.b"):
            ExpressionTree.ensure_attribute_chain(_root().a.b, max_depth=1)

    def test_shorter_chain_is_rejected(self) -> None:
        """A chain shorter than `max_depth` ends on the root too early and is rejected."""
        with pytest.raises(AttributeChainError):
            ExpressionTree.ensure_attribute_chain(_root().a, max_depth=2)


class TestNodeInternals:
    def test_dunder_class_is_not_recorded(self) -> None:
        """Reading `__class__` on a node returns the real class instead of a new node."""
        assert _root().name.__class__ is AttributeNode

    def test_root_formats_empty_at_depth_zero(self) -> None:
        """A root asked for zero steps formats as an empty string."""
        assert ExpressionTree.format(ExpressionTree.new(), max_depth=0) == ""

    def test_element_depth_counts_a_step(self) -> None:
        """An item access counts as one step when a depth is given."""
        assert ExpressionTree.format(_root().a["k"], max_depth=2) == "a['k']"
        assert ExpressionTree.format(_root().a["k"]["j"], max_depth=2) == "['k']['j']"

    def test_nodes_are_abstract(self) -> None:
        """A node subclass must implement the value, format and parents hooks."""

        class Incomplete(ExpressionNode):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # pyright: ignore[reportAbstractUsage]
