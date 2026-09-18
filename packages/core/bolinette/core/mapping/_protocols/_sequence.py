from collections.abc import Iterable, Mapping
from itertools import islice
from typing import Any, ClassVar, override

from peritype import TWrap, wrap_type

from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping._absence import ABSENT, Maybe
from bolinette.core.mapping._protocol import ObjectProtocol
from bolinette.core.mapping._spec import FieldSpec
from bolinette.core.mapping._utils import element_type, main_class


class SequenceProtocol(ObjectProtocol):
    priority = 20
    knows_fields = False
    classes: ClassVar[tuple[type[Any], ...]] = (list, tuple)

    @override
    def matches(self, t: TWrap[Any]) -> bool:
        cls = main_class(t)
        return cls is not None and issubclass(cls, self.classes)

    @override
    def fields(self, t: TWrap[Any]) -> dict[str, FieldSpec]:
        return {}

    @override
    def value_type(self, t: TWrap[Any]) -> TWrap[Any]:
        elem_t = element_type(t)
        return wrap_type(Any) if elem_t is None else elem_t

    @override
    def instance_fields(self, obj: Any, t: TWrap[Any]) -> dict[str, FieldSpec]:
        if isinstance(obj, (str, bytes)) or not isinstance(obj, Iterable):
            return {}
        elem_t = self.value_type(t)
        items: Iterable[Any] = obj  # pyright: ignore[reportUnknownVariableType]
        return {str(i): FieldSpec.from_type(str(i), elem_t) for i, _ in enumerate(items)}

    @override
    def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
        if isinstance(obj, (str, bytes)) or not isinstance(obj, Iterable):
            return ABSENT
        items: Iterable[Any] = obj  # pyright: ignore[reportUnknownVariableType]
        return next(islice(items, int(spec.key), None), ABSENT)

    @override
    def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
        items = [values[key] for key in sorted(values, key=int)]
        cls = main_class(t)
        if cls is None:
            return items
        return cls(items)

    @override
    def assign(self, obj: Any, spec: FieldSpec, value: Any) -> None:
        if not isinstance(obj, list):
            raise TypeError(f"Cannot merge into an immutable sequence of type {type(obj).__qualname__}")
        items: list[Any] = obj  # pyright: ignore[reportUnknownVariableType]
        index = int(spec.key)
        if index < len(items):
            items[index] = value
        else:
            items.append(value)

    @override
    def child_path(self, expr: ExpressionNode, key: str) -> ExpressionNode:
        return expr[int(key)]


class SetProtocol(SequenceProtocol):
    classes = (set, frozenset)

    @override
    def assign(self, obj: Any, spec: FieldSpec, value: Any) -> None:
        if not isinstance(obj, set):
            raise TypeError(f"Cannot merge into an immutable set of type {type(obj).__qualname__}")
        items: set[Any] = obj  # pyright: ignore[reportUnknownVariableType]
        items.add(value)
