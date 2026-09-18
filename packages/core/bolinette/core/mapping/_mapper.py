from collections.abc import Sequence
from typing import Any, cast, overload

from escondite import Cache
from peritype import wrap_type
from soupape import post_init

from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.mapping._decorators import MAPPING_PROFILE_CACHE_KEY, MAPPING_PROTOCOL_CACHE_KEY
from bolinette.core.mapping._profiles import Profile
from bolinette.core.mapping._protocol import ObjectProtocol, ProtocolRegistry
from bolinette.core.mapping._runner import MappingRunner
from bolinette.core.mapping._sequence import MappingSequence
from bolinette.core.mapping._spec import NO_OVERRIDE
from bolinette.core.mapping._value import ValueConverter
from bolinette.core.mapping.exceptions import MappingConfigurationError, MappingError, ValidationError


class Mapper:
    def __init__(self) -> None:
        self.registry = ProtocolRegistry()
        self.converter = ValueConverter()
        self._sequences: dict[int, MappingSequence[Any, Any]] = {}

    @post_init
    def _init_from_cache(self, cache: Cache) -> None:
        for protocol_cls in cache.get(MAPPING_PROTOCOL_CACHE_KEY, hint=type[ObjectProtocol], raises=False):
            self.add_protocol(protocol_cls())
        profiles = [cls() for cls in cache.get(MAPPING_PROFILE_CACHE_KEY, hint=type[Profile], raises=False)]
        self.load_profiles(profiles)

    def add_protocol(self, protocol: ObjectProtocol) -> None:
        self.registry.register(protocol)

    def load_profiles(self, profiles: Sequence[Profile]) -> None:
        completed: dict[int, MappingSequence[Any, Any]] = dict(self._sequences)
        for profile in profiles:
            for sequence in profile.sequences:
                sequence.complete(completed)
                completed[hash(sequence)] = sequence
        self._sequences = completed

    @overload
    def map[DestT](
        self,
        dest_cls: type[DestT],
        src: Any,
        /,
        *,
        dest: DestT | None = None,
        validate: bool = False,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
    ) -> DestT: ...
    @overload
    def map[DestT](
        self,
        src_cls: type[Any],
        dest_cls: type[DestT],
        src: Any,
        /,
        *,
        dest: DestT | None = None,
        validate: bool = False,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
    ) -> DestT: ...
    def map(
        self,
        *args: Any,
        dest: Any | None = None,
        validate: bool = False,
        src_expr: ExpressionNode | None = None,
        dest_expr: ExpressionNode | None = None,
    ) -> Any:
        src_cls: type[Any]
        dest_cls: type[Any]
        src: Any
        match args:
            case (dest_cls, src):
                src_cls = cast(type[Any], type(src))
            case (src_cls, dest_cls, src):
                pass
            case _:
                raise TypeError(Mapper.map, args)
        src_t = wrap_type(src_cls)
        dest_t = wrap_type(dest_cls)
        errors: list[MappingError] | None = [] if validate else None
        runner = MappingRunner(self.registry, self.converter, self._sequences)
        result = runner.map(
            src,
            src_t,
            dest_t,
            dest,
            src_expr if src_expr is not None else ExpressionTree.new(src_t),
            dest_expr if dest_expr is not None else ExpressionTree.new(dest_t),
            errors,
        )
        if errors:
            raise ValidationError(errors)
        return result

    @overload
    def merge[DestT](self, src: Any, dest: DestT, /, *, validate: bool = False) -> DestT: ...
    @overload
    def merge[DestT](self, src_cls: type[Any], src: Any, dest: DestT, /, *, validate: bool = False) -> DestT: ...
    def merge(self, *args: Any, validate: bool = False) -> Any:
        src_cls: type[Any]
        src: Any
        dest: Any
        match args:
            case (src, dest):
                src_cls = cast(type[Any], type(src))
            case (src_cls, src, dest):
                pass
            case _:
                raise TypeError(Mapper.merge, args)
        return self.map(src_cls, cast(type[Any], type(dest)), src, dest=dest, validate=validate)

    def assert_configuration_valid(self) -> None:
        problems: list[str] = []
        for sequence in self._sequences.values():
            dest_protocol = self.registry.resolve(sequence.dest_t)
            if dest_protocol is None:
                problems.append(f"({sequence.src_t} -> {sequence.dest_t}): no protocol for destination")
                continue
            src_protocol = self.registry.resolve(sequence.src_t)
            src_keys = (
                set(src_protocol.fields(sequence.src_t))
                if src_protocol is not None and src_protocol.knows_fields
                else None
            )

            for key, spec in dest_protocol.fields(sequence.dest_t).items():
                override = sequence.overrides.get(key, NO_OVERRIDE)
                if override.ignore or override.read_only or not spec.writable:
                    continue
                if override.source_expr is not None or override.default_factory is not None:
                    continue
                if spec.self_populating or spec.nullable:
                    continue
                if src_keys is not None and key not in src_keys:
                    problems.append(
                        f"({sequence.src_t} -> {sequence.dest_t}): '{key}' is required, has no default, "
                        f"and the source has no matching field. Add .for_attr(lambda d: d.{key}, ...)."
                    )
        if problems:
            raise MappingConfigurationError(problems)
