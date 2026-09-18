from pathlib import Path

from bolinette.core import Bolinette
from tests.web.conftest import AppFactory


async def _new_project(blnt: Bolinette, *args: str) -> int | None:
    return await blnt.run_command(["new", "project", "myapp", "-e", "core", "-e", "web", *args])


class TestNewProjectHooks:
    async def test_the_generated_tree(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        assert await _new_project(blnt) == 0

        assert (tmp_cwd / "myapp" / "server.py").exists()
        assert (tmp_cwd / "myapp" / "controllers" / "__init__.py").exists()

    async def test_the_server_file_content(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        assert (tmp_cwd / "myapp" / "server.py").read_text() == (
            "from bolinette.web import create_asgi_app\n\nfrom myapp import make_bolinette\n\n"
            "app = create_asgi_app(make_bolinette)\n"
        )

    async def test_the_app_file_uses_the_web_extension(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        app_file = (tmp_cwd / "myapp" / "app.py").read_text()
        assert "from bolinette.web import WebExtension" in app_file
        assert "WebExtension()" in app_file

    async def test_the_project_depends_on_the_web_distribution(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        assert '"bolinette-web"' in (tmp_cwd / "pyproject.toml").read_text()

    async def test_a_dry_run_writes_nothing(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        assert await _new_project(blnt, "--dry") == 0

        assert not (tmp_cwd / "myapp").exists()
