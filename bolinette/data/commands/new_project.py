from typing import Any

from bolinette.core import Cache
from bolinette.core.command.commands.new_project import NEW_PROJECT_EVENT, NewProjectHookContext
from bolinette.core.events import on_event


def register_new_project_hooks(cache: Cache) -> None:
    on_event(NEW_PROJECT_EVENT, 100, cache=cache)(create_folders)
    on_event(NEW_PROJECT_EVENT, 110, cache=cache)(create_database_config)


async def create_folders(context: NewProjectHookContext) -> None:
    modules = ["entities", "repositories", "services"]
    for module in modules:
        subfolder = context.package_folder.add_folder(module)
        subfolder.init_package()


async def create_database_config(context: NewProjectHookContext) -> None:
    env_file = context.project_folder.add_folder("env").add_yaml_file("env.local.development.yaml")
    yaml_content: Any = env_file.content or {}
    if not isinstance(yaml_content, dict):
        yaml_content = {}
    if "data" not in yaml_content:
        yaml_content["data"] = {}
    yaml_content["data"]["databases"] = [
        {
            "name": "default",
            "url": "sqlite:///:memory:",
            "echo": True,
        }
    ]
    env_file.content = yaml_content
