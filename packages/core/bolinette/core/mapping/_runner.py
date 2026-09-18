from collections.abc import Mapping, Sequence
from typing import Any, cast

from peritype import TWrap, wrap_type

from bolinette.core.expressions import ExpressionNode
from bolinette.core.mapping._absence import ABSENT, MapMode, Maybe
from bolinette.core.mapping._decision import Action, decide
from bolinette.core.mapping._paths import read_expr
from bolinette.core.mapping._protocol import ObjectProtocol, ProtocolRegistry
from bolinette.core.mapping._sequence import MappingSequence
from bolinette.core.mapping._spec import NO_OVERRIDE, FieldSpec
from bolinette.core.mapping._utils import element_type, is_value_type
from bolinette.core.mapping._value import ValueConverter
from bolinette.core.mapping.exceptions import ConversionError, InstantiationError, MappingError, NoProtocolError


def _wrap_of(value: Any) -> TWrap[Any]:
    return wrap_type(cast(type[Any], type(value)))


class MappingRunner:
    def __init__(
        self,
        registry: ProtocolRegistry,
        converter: ValueConverter,
        sequences: dict[int, MappingSequence[Any, Any]],
    ) -> None:
        self.registry = registry
        self.converter = converter
        self.sequences = sequences

    def map(
        self,
        src: Any,
        src_t: TWrap[Any],
        dest_t: TWrap[Any],
        dest: Any | None,
        src_expr: ExpressionNode,
        dest_expr: ExpressionNode,
        errors: list[MappingError] | None,
    ) -> Any:
        protocol = self.registry.resolve(dest_t)
        if protocol is None:
            raise NoProtocolError(f"No ObjectProtocol registered for {dest_t}", dest=dest_expr)

        src_protocol = self.registry.resolve(src_t)
        src_specs: Mapping[str, FieldSpec] = (
            src_protocol.instance_fields(src, src_t) if src_protocol is not None else {}
        )
        sequence = self.sequences.get(MappingSequence.get_hash(src_t, dest_t))
        mode = MapMode.CREATE if dest is None else MapMode.MERGE
        specs = (
            protocol.fields(dest_t) if protocol.knows_fields else self._specs_from_source(protocol, dest_t, src_specs)
        )

        if sequence is not None and dest is not None:
            for func in sequence.head:
                func(src, dest)

        assigned: dict[str, Any] = {}

        for key, spec in specs.items():
            override = sequence.overrides.get(key, NO_OVERRIDE) if sequence else NO_OVERRIDE
            if override.ignore:
                continue

            field_dest_expr = protocol.child_path(dest_expr, key)
            if override.source_expr is not None:
                field_src_expr = override.source_expr
            elif src_protocol is not None:
                field_src_expr = src_protocol.child_path(src_expr, key)
            else:
                field_src_expr = getattr(src_expr, key)

            if override.source_expr is not None:
                presence: Maybe[Any] = read_expr(override.source_expr, src, self.registry)
            elif src_protocol is not None:
                presence = src_protocol.read_field(src, src_specs.get(key) or spec)
            else:
                presence = getattr(src, key, ABSENT)

            decision = decide(presence, spec, mode, override)
            if decision.action is Action.SKIP:
                continue
            if decision.action is Action.FAIL:
                err = decision.error(decision.reason, dest=field_dest_expr, src=field_src_expr)
                if errors is None:
                    raise err
                errors.append(err)
                continue

            effective = spec if override.use_type is None else spec.with_type(override.use_type)
            try:
                value = self._convert(decision.value, effective, dest, field_src_expr, field_dest_expr, errors)
            except MappingError as err:
                if errors is None:
                    raise
                errors.append(err)
                continue

            if mode is MapMode.CREATE:
                assigned[key] = value
            else:
                protocol.assign(dest, spec, value)

        if mode is MapMode.CREATE:
            if errors:
                return None
            try:
                dest = protocol.construct(dest_t, assigned)
            except MappingError:
                raise
            except Exception as err:
                exc = InstantiationError(f"could not instantiate {dest_t}: {err}", dest=dest_expr)
                if errors is None:
                    raise exc from err
                errors.append(exc)
                return None
            if sequence is not None:
                for func in sequence.head:
                    func(src, dest)

        if sequence is not None:
            for func in sequence.tail:
                func(src, dest)

        return dest

    def _convert(
        self,
        value: Any,
        spec: FieldSpec,
        parent_dest: Any,
        src_expr: ExpressionNode,
        dest_expr: ExpressionNode,
        errors: list[MappingError] | None,
    ) -> Any:
        if value is None:
            return None

        elem_t = element_type(spec.type)
        if elem_t is not None:
            elem_protocol = self.registry.resolve(elem_t)
            if elem_protocol is not None and self._is_structure(elem_t, elem_protocol):
                if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
                    raise ConversionError("expected an iterable", target=spec.type, dest=dest_expr, src=src_expr)
                items: Sequence[Any] = value  # pyright: ignore[reportUnknownVariableType]
                mapped = [
                    self.map(item, _wrap_of(item), elem_t, None, src_expr[i], dest_expr[i], errors)
                    for i, item in enumerate(items)
                ]
                existing = getattr(parent_dest, spec.key, None) if parent_dest is not None else None
                owner = self.registry.resolve(_wrap_of(parent_dest)) if parent_dest is not None else None
                if owner is not None and existing is not None:
                    return owner.merge_collection(existing, mapped)
                return mapped
        else:
            nested = self.registry.resolve(spec.type)
            if nested is not None and self._is_structure(spec.type, nested):
                existing = getattr(parent_dest, spec.key, None) if parent_dest is not None else None
                return self.map(value, _wrap_of(value), spec.type, existing, src_expr, dest_expr, errors)

        return self.converter.convert(value, spec, dest_expr, src_expr)

    @staticmethod
    def _specs_from_source(
        protocol: ObjectProtocol, dest_t: TWrap[Any], src_specs: Mapping[str, FieldSpec]
    ) -> dict[str, FieldSpec]:
        value_t = protocol.value_type(dest_t)
        nullable = value_t.nullable or value_t.match(Any).is_exact
        return {key: FieldSpec.from_type(key, value_t, nullable=nullable, has_default=True) for key in src_specs}

    @staticmethod
    def _is_structure(t: TWrap[Any], protocol: ObjectProtocol) -> bool:
        if is_value_type(t) or not protocol.knows_fields:
            return False
        return bool(protocol.fields(t))
