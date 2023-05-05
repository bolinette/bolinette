from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bolinette import meta
from bolinette.exceptions import InjectionError
from bolinette.ext.data.relational import EntityManager, RelationalDatabase, SessionManager
from bolinette.injection.resolver import ArgResolverOptions, injection_arg_resolver


@injection_arg_resolver(priority=100)
class EntityTypeArgResolver:
    def __init__(self, entities: EntityManager) -> None:
        self.entities = entities

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.t.cls is type and self.entities.is_entity_type(options.t.vars[0])

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        return options.name, options.t.vars[0]


@injection_arg_resolver(priority=110, scoped=True)
class AsyncSessionArgResolver:
    def __init__(self, entities: EntityManager, sessions: SessionManager) -> None:
        self.entities = entities
        self.sessions = sessions

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.t.cls is AsyncSession

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        if options.caller_type_vars is None:
            raise InjectionError(
                "Cannot inject session in non generic context", func=options.caller, param=options.name
            )
        entity_type = options.caller_type_vars[0]
        if not self.entities.is_entity_type(entity_type):
            raise InjectionError(
                f"Type {entity_type} is not registered as an entity", func=options.caller, param=options.name
            )
        engine = meta.get(entity_type, RelationalDatabase)
        return options.name, self.sessions.get(engine._name)
