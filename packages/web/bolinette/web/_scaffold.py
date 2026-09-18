from bolinette.core.extensions import NewProjectHookContext


async def create_server_file(context: NewProjectHookContext) -> None:
    server_file = context.package_folder.add_file("server.py")
    server_file.append(f"""from bolinette.web import create_asgi_app

from {context.name} import make_bolinette

app = create_asgi_app(make_bolinette)""")


async def create_controllers_package(context: NewProjectHookContext) -> None:
    context.package_folder.add_folder("controllers").init_package()
