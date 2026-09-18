from dataclasses import dataclass
from typing import Any

from peritype import TWrap, wrap_type

from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping._absence import Generation


@dataclass(frozen=True, slots=True)
class FieldSpec:
    key: str

    type: TWrap[Any]

    nullable: bool = False
    generation: Generation = Generation.NONE
    has_default: bool = False
    writable: bool = True

    lazy: bool = False

    @property
    def self_populating(self) -> bool:
        return self.has_default or self.generation is not Generation.NONE

    @staticmethod
    def from_type(key: str, t: TWrap[Any] | Any, **kwargs: Any) -> "FieldSpec":
        t = wrap_type(t)
        kwargs.setdefault("nullable", t.nullable)
        return FieldSpec(key=key, type=t, **kwargs)

    def with_type(self, t: TWrap[Any]) -> "FieldSpec":
        return FieldSpec(
            key=self.key,
            type=t,
            nullable=self.nullable,
            generation=self.generation,
            has_default=self.has_default,
            writable=self.writable,
            lazy=self.lazy,
        )


@dataclass(frozen=True, slots=True)
class FieldOverride:
    ignore: bool = False
    read_only: bool = False
    allow_write: bool = False
    source_expr: ExpressionNode | None = None
    use_type: TWrap[Any] | None = None
    default_factory: Any = None


NO_OVERRIDE = FieldOverride()
