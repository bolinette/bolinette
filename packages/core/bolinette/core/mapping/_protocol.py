from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from peritype import TWrap, wrap_type

from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping._absence import Maybe
from bolinette.core.mapping._spec import FieldSpec


class ObjectProtocol(ABC):
    priority: int = 0
    knows_fields: bool = True

    @abstractmethod
    def matches(self, t: TWrap[Any]) -> bool: ...

    @abstractmethod
    def fields(self, t: TWrap[Any]) -> Mapping[str, FieldSpec]: ...

    def instance_fields(self, obj: Any, t: TWrap[Any]) -> Mapping[str, FieldSpec]:
        return self.fields(t)

    def value_type(self, t: TWrap[Any]) -> TWrap[Any]:
        return wrap_type(Any)

    @abstractmethod
    def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]: ...

    @abstractmethod
    def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any: ...

    def assign(self, obj: Any, spec: FieldSpec, value: Any) -> None:
        setattr(obj, spec.key, value)

    def child_path(self, expr: ExpressionNode, key: str) -> ExpressionNode:
        return getattr(expr, key)

    def merge_collection(self, existing: Any, incoming: list[Any]) -> Any:
        if isinstance(existing, list):
            existing[:] = incoming
            return existing  # pyright: ignore[reportUnknownVariableType]
        if isinstance(existing, set):
            existing.clear()
            existing.update(incoming)  # pyright: ignore[reportUnknownMemberType]
            return existing  # pyright: ignore[reportUnknownVariableType]
        return incoming


class ProtocolRegistry:
    def __init__(self) -> None:
        self._protocols: list[ObjectProtocol] = []
        self._cache: dict[TWrap[Any], ObjectProtocol | None] = {}

    def register(self, protocol: ObjectProtocol) -> None:
        self._protocols.append(protocol)
        self._protocols.sort(key=lambda p: p.priority, reverse=True)
        self._cache.clear()

    def resolve(self, t: TWrap[Any]) -> ObjectProtocol | None:
        if t in self._cache:
            return self._cache[t]
        found = next((p for p in self._protocols if p.matches(t)), None)
        self._cache[t] = found
        return found
