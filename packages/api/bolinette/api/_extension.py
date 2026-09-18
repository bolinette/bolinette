from collections.abc import Sequence
from typing import Any, override

from escondite import Cache
from soupape import ServiceCollection

from bolinette.api._autoroute import build_autoroutes
from bolinette.api._scaffold import create_example_controller, create_example_entity
from bolinette.core import CoreExtension
from bolinette.core.extensions import Extension, NewProjectHook
from bolinette.data import DataExtension
from bolinette.data.relational import discover_entities
from bolinette.web import WebExtension
from bolinette.web._controller import ControllerMeta


class ApiExtension(Extension):
    name = "api"
    dependencies: Sequence[type[Extension]] = (CoreExtension, DataExtension, WebExtension)

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        entities = discover_entities(cache)
        for ctrl_cls in cache.get(ControllerMeta.KEY, hint=type[Any], raises=False):
            build_autoroutes(ctrl_cls, entities)

    @override
    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return (create_example_entity, create_example_controller)
