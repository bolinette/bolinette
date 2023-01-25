from typing import Any

from bolinette.ext.data import EntityManager
from bolinette.inject import ArgResolverOptions, injection_arg_resolver


@injection_arg_resolver(priority=100)
class EntityTypeArgResolver:
    def __init__(self, entities: EntityManager) -> None:
        self.entities = entities

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.cls is type and self.entities.is_entity_type(options.type_vars[0])

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        return options.name, options.type_vars[0]
