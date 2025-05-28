from typing import Any

from bolinette.core import meta
from bolinette.core.environment import Environment
from bolinette.core.environment.sections import EnvSectionMeta
from bolinette.core.expressions import ExpressionTree
from bolinette.core.injection.resolver import ArgResolverOptions
from bolinette.core.logging import Logger
from bolinette.core.mapping import Mapper
from bolinette.core.types import Type


class EnvironmentSectionResolver:
    def __init__(self, env: Environment, mapper: Mapper) -> None:
        self.env = env
        self.mapper = mapper

    def supports(self, options: ArgResolverOptions) -> bool:
        return meta.has(options.t.cls, EnvSectionMeta)

    def resolve(self, options: ArgResolverOptions) -> Logger[Any]:
        section_name = meta.get(options.t.cls, EnvSectionMeta).name
        return self.mapper.map(
            dict[str, Any],
            options.t.cls,
            self.env.config.get(section_name, {}),
            src_expr=ExpressionTree.new(Type(Environment))[section_name],
        )
