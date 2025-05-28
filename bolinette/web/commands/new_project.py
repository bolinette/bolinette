from bolinette.core import Cache
from bolinette.core.command.commands.new_project import NEW_PROJECT_EVENT, NewProjectHookContext
from bolinette.core.events import on_event


def register_new_project_hooks(cache: Cache) -> None:
    on_event(NEW_PROJECT_EVENT, 200, cache=cache)(create_server_file)
    on_event(NEW_PROJECT_EVENT, 210, cache=cache)(create_folders)


async def create_server_file(context: NewProjectHookContext) -> None:
    server_file = context.package_folder.add_file("server.py")
    server_file.append(f"""from bolinette.web.asgi import AsgiApplication
from {context.name} import make_bolinette

app = AsgiApplication(make_bolinette()).get_app()""")


async def create_folders(context: NewProjectHookContext) -> None:
    modules = ["controllers"]
    for module in modules:
        subfolder = context.package_folder.add_folder(module)
        subfolder.init_package()
