import importlib
from importlib.metadata import entry_points
from pathlib import Path
from typing import Annotated, cast

from soupape import AsyncInjector

from bolinette import core
from bolinette.core.commands import CommandArg, CommandOption
from bolinette.core.exceptions import InitError
from bolinette.core.extensions import Extension, ExtensionSource, NewProjectHookContext, resolve_extensions
from bolinette.core.fs import FSFolder


async def new_project(
    logger: "core.Logger[core.Bolinette]",
    injector: AsyncInjector,
    name: Annotated[str, CommandArg()],
    extensions: Annotated[list[str] | None, CommandOption("e")] = None,
    dry: Annotated[bool, CommandOption("d")] = False,
) -> int:
    project_folder = FSFolder(Path.cwd())
    module_folder = project_folder.add_folder(name)

    loaded_extensions = _load_extensions(extensions)
    from bolinette.core import CoreExtension

    extension_names = [ext.name for ext in loaded_extensions]

    print(f"Creating project {name} with extensions: {', '.join(extension_names)}")

    def on_failure(code: int) -> None:
        logger.error(f"Failed to create project {name} with code {code}")
        raise SystemExit(code)

    context = NewProjectHookContext(
        name=name,
        extensions=loaded_extensions,
        extension_names=extension_names,
        extension_sources=[_extension_source(ext) for ext in loaded_extensions if not isinstance(ext, CoreExtension)],
        dependencies=_extension_distributions(loaded_extensions),
        project_folder=project_folder,
        package_folder=module_folder,
        on_failure=on_failure,
    )

    async with injector.get_scoped_injector() as scoped_injector:
        scoped_injector.services.add_scoped(NewProjectHookContext, lambda: context)
        for ext in loaded_extensions:
            for hook in ext.get_new_project_hooks():
                await scoped_injector.call(hook)

    if not dry:
        project_folder.commit()

    return 0


ENTRY_POINT_GROUP = "bolinette.extensions"


def _discover_extension_types() -> dict[str, type[Extension]]:
    found: dict[str, type[Extension]] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        found[entry_point.name] = cast(type[Extension], entry_point.load())
    return found


def _extension_distributions(extensions: list[Extension]) -> list[str]:
    by_type: dict[type[Extension], str] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        if entry_point.dist is not None:
            by_type[cast(type[Extension], entry_point.load())] = entry_point.dist.name
    found: list[str] = []
    for ext in extensions:
        dist = by_type.get(type(ext))
        if dist is not None and dist not in found:
            found.append(dist)
    return found


def _import_extension_type(path: str) -> type[Extension]:
    module_name, _, attr = path.partition(":")
    if not attr:
        raise InitError(f"Extension '{path}' must be an entry point name or a 'module:ClassName' path")
    try:
        module = importlib.import_module(module_name)
    except ImportError as err:
        raise InitError(f"Extension module '{module_name}' could not be imported") from err
    if not hasattr(module, attr):
        raise InitError(f"Module '{module_name}' has no attribute '{attr}'")
    return cast(type[Extension], getattr(module, attr))


def _load_extensions(extension_names: list[str] | None) -> list[Extension]:
    known = _discover_extension_types()
    if not extension_names:
        types = list(known.values())
    else:
        types = [known[name] if name in known else _import_extension_type(name) for name in extension_names]
    from bolinette.core import CoreExtension

    return resolve_extensions([t() for t in types], implicit=[CoreExtension])


def _extension_source(ext: Extension) -> ExtensionSource:
    ext_type = type(ext)
    module = ext_type.__module__
    # prefer the public package when the class is re-exported from its parent package
    parent = module.rpartition(".")[0]
    if parent:
        try:
            if getattr(importlib.import_module(parent), ext_type.__qualname__, None) is ext_type:
                module = parent
        except ImportError:
            pass
    return ExtensionSource(module, ext_type.__qualname__)


async def create_dunder_init(context: NewProjectHookContext) -> None:
    dunder_init = context.package_folder.init_package()
    dunder_init.append(f"from {context.name}.app import make_bolinette as make_bolinette")


async def create_app_file(context: NewProjectHookContext) -> None:
    app_file = context.package_folder.add_file("app.py")
    imports = "".join(f"{src.import_line}\n" for src in context.extension_sources)
    instances = ", ".join(f"{src.attr}()" for src in context.extension_sources)
    app_file.append(f"""from bolinette import core
{imports}

async def make_bolinette() -> core.Bolinette:
    return await core.make_bolinette(extensions=[{instances}])""")


async def update_pyproject_toml(context: NewProjectHookContext) -> None:
    pyproject_toml = context.project_folder.add_file("pyproject.toml")
    if not pyproject_toml.exists():
        dependencies = "".join(f'    "{dep}",\n' for dep in context.dependencies)
        pyproject_toml.append(
            "[project]",
            f'name = "{context.name}"',
            'version = "0.1.0"',
            f'description = "TODO: describe the {context.name} project"',
            'requires-python = ">=3.13"',
            f"dependencies = [\n{dependencies}]",
        )
    pyproject_toml.append(
        "",
        "[tool.bolinette]",
        f'project = "{context.name}"',
        f'app_factory = "{context.name}:make_bolinette"',
    )


async def create_env_files(context: NewProjectHookContext) -> None:
    env_folder = context.project_folder.add_folder("env")
    env_folder.add_file(".profile").append("development")

    env_folder.add_file("env.toml").append(
        "[core]",
        "debug = false",
    )
    env_folder.add_file("env.development.toml").append(
        "[core]",
        "debug = true",
        "[[core.logging]]",
        'level = "DEBUG"',
        'type = "stderr"',
        "color = true",
    )
    env_folder.add_file("env.test.toml").append(
        "[core]",
        "debug = false",
        "[[core.logging]]",
        'level = "INFO"',
        'type = "stderr"',
        "color = true",
        "[[core.logging]]",
        'level = "INFO"',
        'type = "file"',
        'path = "logs/test.log"',
    )
    env_folder.add_file("env.production.toml").append(
        "[core]",
        "debug = false",
        "[[core.logging]]",
        'level = "INFO"',
        'type = "stderr"',
        "color = true",
        "[[core.logging]]",
        'level = "INFO"',
        'type = "file"',
        'path = "logs/production.log"',
    )
    env_folder.add_file(".gitignore").append("env.local.*.toml")


async def create_gitignore(context: NewProjectHookContext) -> None:
    gitignore = context.project_folder.add_file(".gitignore")
    gitignore.append("__pycache__/")
