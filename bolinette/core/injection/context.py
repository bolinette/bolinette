from typing import Any

from bolinette.core.injection.registration import InjectionStrategy
from bolinette.core.types import Function, Type


class InjectionContext:
    def __init__(
        self,
        origin: Type[Any] | Function[..., Any],
        strategy: InjectionStrategy,
        arg_name: str,
        default_set: bool,
        default: Any,
    ) -> None:
        self.origin = origin
        self.strategy = strategy
        self.arg_name = arg_name
        self.default_set = default_set
        self.default = default
