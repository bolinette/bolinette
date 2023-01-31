from typing import Any

from bolinette.ext.data import EntityManager
from bolinette.ext.data.entity import EntityMeta
from bolinette.ext.data.sessions import SessionManager, ScopedSession
from bolinette import meta
from bolinette.exceptions import InjectionError
from bolinette.inject import ArgResolverOptions, injection_arg_resolver


@injection_arg_resolver(priority=100)
class EntityTypeArgResolver:
    def __init__(self, entities: EntityManager) -> None:
        self.entities = entities

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.cls is type and self.entities.is_entity_type(options.type_vars[0])

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        return options.name, options.type_vars[0]


@injection_arg_resolver(priority=110, scoped=True)
class AsyncSessionArgResolver:
    def __init__(self, entities: EntityManager, sessions: SessionManager) -> None:
        self.entities = entities
        self.sessions = sessions

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.cls is ScopedSession

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        entity_type = options.type_vars[0]
        if not self.entities.is_entity_type(entity_type):
            raise InjectionError(
                f"Type {entity_type} is not registered as an entity", func=options.caller, param=options.name
            )
        _meta = meta.get(entity_type, EntityMeta)
        if _meta.database not in self.sessions:
            raise InjectionError(
                f"No session has been started for database '{_meta.database}'", func=options.caller, param=options.name
            )
        return options.name, self.sessions.get(_meta.database)
