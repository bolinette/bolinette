from bolinette.core.extensions import NewProjectHookContext


async def create_data_packages(context: NewProjectHookContext) -> None:
    for name in ("entities", "repositories", "services"):
        context.package_folder.add_folder(name).init_package()


async def create_database_config(context: NewProjectHookContext) -> None:
    env_file = context.project_folder.add_folder("env").add_file("env.local.development.toml")
    env_file.append(
        "[[data.databases]]",
        'name = "default"',
        'url = "sqlite+aiosqlite://"',
        "echo = true",
    )
