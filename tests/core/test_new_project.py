"""The bundled `new project` command and its hooks."""

import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import override

import pytest
from escondite import Cache
from soupape import ServiceCollection

from bolinette.core import Bolinette, CoreExtension, startup
from bolinette.core.commands._bundled._new_project import _extension_source  # pyright: ignore[reportPrivateUsage]
from bolinette.core.exceptions import InitError
from bolinette.core.extensions import Extension, ExtensionSource, NewProjectHook, NewProjectHookContext
from tests.core.conftest import AppFactory


class DemoExtension(Extension):
    name = "demo"
    dependencies: Sequence[type[Extension]] = ()

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass


_MODULE = __name__

seen_contexts: list[NewProjectHookContext] = []


async def record_context(context: NewProjectHookContext) -> None:
    seen_contexts.append(context)


async def add_readme(context: NewProjectHookContext, cache: Cache) -> None:
    context.project_folder.add_file("README.md").append(f"# {context.name}")


async def fail(context: NewProjectHookContext) -> None:
    context.on_failure(3)


class HookExtension(Extension):
    name = "hook"

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass

    @override
    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return (record_context, add_readme)


class FailingExtension(Extension):
    name = "failing"

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass

    @override
    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return (fail,)


async def _run(blnt: Bolinette, *args: str) -> int | None:
    return await blnt.run_command(["new", "project", *args])


hook_calls: list[str] = []


async def base_hook(context: NewProjectHookContext) -> None:
    hook_calls.append("base")


async def child_hook(context: NewProjectHookContext) -> None:
    hook_calls.append("child")


class BaseExtension(Extension):
    name = "base"

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass

    @override
    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return (base_hook,)


class ChildExtension(Extension):
    name = "child"
    dependencies = (BaseExtension,)

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        pass

    @override
    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return (child_hook,)


class TestNewProject:
    async def test_dry_run_writes_nothing(
        self, make_app: AppFactory, tmp_cwd: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With `--dry` the project is described but nothing reaches the disk."""
        blnt = await make_app()

        assert await _run(blnt, "myapp", "-e", "core", "--dry") == 0

        assert list(tmp_cwd.iterdir()) == []
        assert "Creating project myapp with extensions: core" in capsys.readouterr().out

    async def test_does_not_start_the_application(self, make_app: AppFactory, cache: Cache) -> None:
        """Scaffolding runs from the bare tool app and never triggers its startup."""
        calls: list[str] = []

        @startup(cache=cache)
        async def init() -> None:
            calls.append("startup")

        blnt = await make_app()
        await _run(blnt, "myapp", "--dry")

        assert calls == []
        assert not blnt.started

    async def test_creates_package_and_files(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """The project package, app factory, env files and gitignore are created."""
        blnt = await make_app()

        await _run(blnt, "myapp", "-e", "core")

        assert (
            tmp_cwd / "myapp" / "__init__.py"
        ).read_text() == "from myapp.app import make_bolinette as make_bolinette\n"
        app = (tmp_cwd / "myapp" / "app.py").read_text()
        assert "from bolinette import core" in app
        assert "return await core.make_bolinette(extensions=[])" in app
        assert (tmp_cwd / "env" / ".profile").read_text() == "development\n"
        assert {p.name for p in (tmp_cwd / "env").iterdir()} == {
            ".profile",
            ".gitignore",
            "env.toml",
            "env.development.toml",
            "env.test.toml",
            "env.production.toml",
        }
        assert (tmp_cwd / ".gitignore").read_text() == "__pycache__/\n"

    async def test_debug_is_only_enabled_in_development(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """The generated profiles keep debug off except for development."""
        blnt = await make_app()

        await _run(blnt, "myapp")

        debug = {
            name: tomllib.loads((tmp_cwd / "env" / f"{name}.toml").read_text())["core"]["debug"]
            for name in ("env", "env.development", "env.test", "env.production")
        }
        assert debug == {"env": False, "env.development": True, "env.test": False, "env.production": False}

    async def test_pyproject_is_extended(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """An existing `pyproject.toml` only gets a `tool.bolinette` table appended."""
        (tmp_cwd / "pyproject.toml").write_text('[project]\nname = "myapp"\n')
        blnt = await make_app()

        await _run(blnt, "myapp")

        assert (tmp_cwd / "pyproject.toml").read_text() == (
            '[project]\nname = "myapp"\n\n[tool.bolinette]\nproject = "myapp"\napp_factory = "myapp:make_bolinette"\n'
        )

    async def test_pyproject_is_created_with_placeholders(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """Without a `pyproject.toml` a minimal valid one is written, depending on the selected distributions."""
        blnt = await make_app()

        await _run(blnt, "myapp", "-e", "core")

        content = (tmp_cwd / "pyproject.toml").read_text()
        assert content == (
            "[project]\n"
            'name = "myapp"\n'
            'version = "0.1.0"\n'
            'description = "TODO: describe the myapp project"\n'
            'requires-python = ">=3.13"\n'
            "dependencies = [\n"
            '    "bolinette",\n'
            "]\n"
            "\n"
            "[tool.bolinette]\n"
            'project = "myapp"\n'
            'app_factory = "myapp:make_bolinette"\n'
        )
        assert tomllib.loads(content)["project"]["name"] == "myapp"

    async def test_extensions_by_entry_point_name_and_path(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """Extensions are given by entry point name or `module:Class` path and land in the app factory."""
        blnt = await make_app()

        await _run(blnt, "myapp", "-e", "core", "-e", f"{_MODULE}:DemoExtension")

        app = (tmp_cwd / "myapp" / "app.py").read_text()
        assert f"from {_MODULE} import DemoExtension" in app
        assert "extensions=[DemoExtension()]" in app

    async def test_invalid_extension_paths(self, make_app: AppFactory) -> None:
        """A malformed path, an unknown module or a missing attribute are reported as `InitError`."""
        blnt = await make_app()

        with pytest.raises(InitError, match="entry point name or a 'module:ClassName' path"):
            await _run(blnt, "myapp", "-e", "nope", "--dry")
        with pytest.raises(InitError, match="could not be imported"):
            await _run(blnt, "myapp", "-e", "nope_module:Ext", "--dry")
        with pytest.raises(InitError, match="has no attribute"):
            await _run(blnt, "myapp", "-e", f"{_MODULE}:Nope", "--dry")

    async def test_extension_hooks_receive_the_context(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """Hooks declared on the selected extensions are injected with the context and can add files."""
        seen_contexts.clear()
        blnt = await make_app()

        await _run(blnt, "myapp", "-e", f"{_MODULE}:HookExtension")

        assert (tmp_cwd / "README.md").read_text() == "# myapp\n"
        (context,) = seen_contexts
        assert context.extension_names == ["core", "hook"]
        assert context.dependencies == ["bolinette"]
        assert context.extension_sources == [ExtensionSource(_MODULE, "HookExtension")]
        assert context.package_folder.path == tmp_cwd / "myapp"

    async def test_on_failure_exits(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """A hook can abort the command with an exit code, and nothing is written."""
        blnt = await make_app()

        with pytest.raises(SystemExit) as info:
            await _run(blnt, "myapp", "-e", f"{_MODULE}:FailingExtension")

        assert info.value.code == 3
        assert list(tmp_cwd.iterdir()) == []

    async def test_hooks_run_in_dependency_order(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """Hooks follow the extension dependency order: core first, then a dependency before its dependent."""
        hook_calls.clear()
        blnt = await make_app()

        await _run(blnt, "myapp", "-e", f"{_MODULE}:ChildExtension", "--dry")

        assert hook_calls == ["base", "child"]

    async def test_core_hooks_run_before_extension_hooks(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        """A selected extension's hook sees the files created by the core hooks."""
        seen_contexts.clear()
        blnt = await make_app()

        await _run(blnt, "myapp", "-e", f"{_MODULE}:HookExtension", "--dry")

        assert "app.py" in seen_contexts[0].package_folder


class TestNewProjectHooks:
    def test_core_declares_its_hooks(self) -> None:
        """The core extension lists the built-in scaffolding hooks in run order."""
        names = [hook.__name__ for hook in CoreExtension().get_new_project_hooks()]

        assert names == [
            "create_dunder_init",
            "create_app_file",
            "update_pyproject_toml",
            "create_env_files",
            "create_gitignore",
        ]

    def test_extensions_have_no_hooks_by_default(self) -> None:
        """An extension that does not override the method has no scaffolding hooks."""
        assert DemoExtension().get_new_project_hooks() == ()


class TestExtensionSource:
    def test_import_line(self) -> None:
        """A source renders as a `from module import attr` line."""
        assert ExtensionSource("pkg.mod", "Ext").import_line == "from pkg.mod import Ext"

    def test_prefers_public_reexport(self) -> None:
        """A class re-exported by its parent package is imported from that package."""
        assert _extension_source(CoreExtension()) == ExtensionSource("bolinette.core", "CoreExtension")

    def test_keeps_module_without_reexport(self) -> None:
        """A class not re-exported by its parent keeps its defining module."""
        assert _extension_source(DemoExtension()) == ExtensionSource(_MODULE, "DemoExtension")

    def test_unimportable_parent_is_ignored(self) -> None:
        """A parent package that cannot be imported leaves the module unchanged."""

        class Orphan(DemoExtension):
            pass

        Orphan.__module__ = "nope_pkg.orphan"
        Orphan.__qualname__ = "Orphan"

        assert _extension_source(Orphan()) == ExtensionSource("nope_pkg.orphan", "Orphan")
