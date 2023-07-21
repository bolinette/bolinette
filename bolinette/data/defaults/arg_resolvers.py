from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bolinette.core import meta
from bolinette.core.exceptions import InjectionError
from bolinette.core.injection.resolver import ArgResolverOptions
from bolinette.data.relational import EntityManager, RelationalDatabase, SessionManager


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
        return options.name, self.sessions.get(engine.name)
