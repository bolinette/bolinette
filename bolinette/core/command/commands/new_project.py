import importlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, cast

from bolinette import core
from bolinette.core import Cache
from bolinette.core.command import Argument
from bolinette.core.events import EventDispatcher, on_event
from bolinette.core.extensions import Extension, ExtensionModule, sort_extensions
from bolinette.core.fs import FSFolder
from bolinette.core.injection import Injection
from bolinette.core.logging import Logger


async def new_project(
    logger: Logger["core.Bolinette"],
    inject: Injection,
    events: EventDispatcher,
    name: Annotated[str, Argument()],
    extensions: Annotated[list[str] | None, Argument("option", "e")] = None,
    dry: Annotated[bool, Argument("option", "d")] = False,
) -> int:
    project_folder = FSFolder(Path.cwd())
    module_folder = project_folder.add_folder(name)

    cache = Cache()
    loaded_extensions = _load_extensions(cache, extensions)
    extension_names = [ext.name.split(".")[-1] for ext in loaded_extensions]

    print(f"Creating project {name} with extensions: {', '.join(extension_names)}")

    def on_failure(code: int) -> None:
        logger.error(f"Failed to create project {name} with code {code}")
        raise SystemExit(code)

    context = NewProjectHookContext(
        name=name,
        extensions=loaded_extensions,
        extension_names=extension_names,
        project_folder=project_folder,
        package_folder=module_folder,
        on_failure=on_failure,
    )

    async with inject.get_async_scoped_session() as session:
        session.add_instance(NewProjectHookContext, context)
        await events.dispatch(NEW_PROJECT_EVENT, session=session, cache=cache)

    if not dry:
        project_folder.commit()

    return 0


def _import_module(name: str) -> ExtensionModule[Extension] | None:
    try:
        module = importlib.import_module(name)
    except ImportError as err:
        print(err)
        return None
    if hasattr(module, "__blnt_ext__"):
        return cast(ExtensionModule[Extension], module)
    return None


def _import_extension(cache: Cache, name: str) -> Extension | None:
    module = _import_module(name)
    if module is None:
        return None
    return module.__blnt_ext__(cache)


def _load_dependencies(cache: Cache, extension: Extension, loaded_extensions: list[Extension]) -> list[Extension]:
    loaded_types = {type(e) for e in loaded_extensions}
    for dep_module in extension.dependencies:
        ext_type = dep_module.__blnt_ext__
        if ext_type not in loaded_types:
            dep_ext = ext_type(cache)
            loaded_extensions.append(dep_ext)
            loaded_types.add(ext_type)
            loaded_extensions = _load_dependencies(cache, dep_ext, loaded_extensions)
    return loaded_extensions


def _load_extensions(cache: Cache, extension_names: list[str] | None) -> list[Extension]:
    blnt_modules = _detect_extension_modules()
    if not extension_names:
        return [module.__blnt_ext__(cache) for module in blnt_modules.values()]
    loaded_extensions: list[Extension] = []
    for name in extension_names:
        if name in blnt_modules:
            extension = blnt_modules[name].__blnt_ext__(cache)
        else:
            extension = _import_extension(cache, name)
            if extension is None:
                raise ImportError(f"Extension {name} not found")
        loaded_extensions.append(extension)
        loaded_extensions = _load_dependencies(cache, extension, loaded_extensions)
    return sort_extensions(loaded_extensions)


def _detect_extension_modules() -> dict[str, ExtensionModule[Extension]]:
    bolinette_path = Path(core.__file__).parent.parent
    extensions: dict[str, ExtensionModule[Extension]] = {}
    for submodule_path in bolinette_path.iterdir():
        if not submodule_path.is_dir():
            continue
        module = _import_module(f"bolinette.{submodule_path.name}")
        if module is not None:
            extensions[submodule_path.name] = module
    return extensions


@dataclass
class NewProjectHookContext:
    name: str
    extensions: list[Extension]
    extension_names: list[str]
    project_folder: FSFolder
    package_folder: FSFolder
    on_failure: Callable[[int], None]


NEW_PROJECT_EVENT = "blnt:cmd:new_project"


def register_new_project_hooks(cache: Cache) -> None:
    on_event(NEW_PROJECT_EVENT, 10, cache=cache)(create_dunder_init)
    on_event(NEW_PROJECT_EVENT, 20, cache=cache)(create_app_file)
    on_event(NEW_PROJECT_EVENT, 30, cache=cache)(update_pyproject_toml)
    on_event(NEW_PROJECT_EVENT, 40, cache=cache)(create_env_files)
    on_event(NEW_PROJECT_EVENT, 50, cache=cache)(create_gitignore)


async def create_dunder_init(context: NewProjectHookContext) -> None:
    dunder_init = context.package_folder.init_package()
    dunder_init.append(f"from {context.name}.app import make_bolinette as make_bolinette")


async def create_app_file(context: NewProjectHookContext) -> None:
    app_file = context.package_folder.add_file("app.py")
    app_file.append(f"""from bolinette import {", ".join(context.extension_names)}
from bolinette.core import Bolinette


def make_bolinette() -> Bolinette:
    blnt = Bolinette()
    {"\n    ".join([f"blnt.use_extension({ext})" for ext in context.extension_names])}
    return blnt.build()""")


async def update_pyproject_toml(context: NewProjectHookContext) -> None:
    pyproject_toml = context.project_folder.add_file("pyproject.toml")
    pyproject_toml.append(f"""\n[tool.bolinette]
project = "{context.name}"
app_factory = "{context.name}:make_bolinette\"""")


async def create_env_files(context: NewProjectHookContext) -> None:
    env_folder = context.project_folder.add_folder("env")
    env_folder.add_file(".profile").append("development")

    env_folder.add_yaml_file("env.yaml").content = {"core": {"debug": False}}
    env_folder.add_yaml_file("env.development.yaml").content = {
        "core": {
            "debug": True,
            "logging": [
                {"level": "DEBUG", "type": "stderr", "color": True},
            ],
        }
    }
    env_folder.add_yaml_file("env.test.yaml").content = {
        "core": {
            "debug": False,
            "logging": [
                {"level": "INFO", "type": "stderr", "color": True},
                {"level": "INFO", "type": "file", "path": "logs/test.log"},
            ],
        }
    }
    env_folder.add_yaml_file("env.production.yaml").content = {
        "core": {
            "debug": False,
            "logging": [
                {"level": "INFO", "type": "stderr", "color": True},
                {"level": "INFO", "type": "file", "path": "logs/production.log"},
            ],
        }
    }
    env_folder.add_file(".gitignore").append("env.local.*.yaml\n")


async def create_gitignore(context: NewProjectHookContext) -> None:
    gitignore = context.project_folder.add_file(".gitignore")
    gitignore.append("__pycache__/")
