from typing import Any

import pydantic
from peritype import TWrap
from pydantic import TypeAdapter

from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping._spec import FieldSpec
from bolinette.core.mapping.exceptions import ConversionError


class ValueConverter:
    def __init__(self, *, strict: bool = False) -> None:
        self._strict = strict
        self._adapters: dict[TWrap[Any], TypeAdapter[Any]] = {}

    def _adapter(self, t: TWrap[Any]) -> TypeAdapter[Any]:
        if t not in self._adapters:
            self._adapters[t] = TypeAdapter(t.value_type)
        return self._adapters[t]

    def convert(self, value: Any, spec: FieldSpec, dest: ExpressionNode, src: ExpressionNode) -> Any:
        try:
            return self._adapter(spec.type).validate_python(value, strict=self._strict)
        except pydantic.ValidationError as err:
            details = err.errors()
            reason = str(details[0]["msg"]) if details else "invalid"
            raise ConversionError(
                f"Could not convert {value!r} to {spec.type} ({reason})",
                target=spec.type,
                dest=dest,
                src=src,
            ) from err
