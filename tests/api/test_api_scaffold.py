from pathlib import Path

from bolinette.core import Bolinette
from tests.api.conftest import AppFactory


async def _new_project(blnt: Bolinette, *args: str) -> int | None:
    return await blnt.run_command(["new", "project", "myapp", "-e", "api", *args])


def _read(tmp_cwd: Path, *parts: str) -> str:
    return (tmp_cwd.joinpath(*parts)).read_text()


class TestGeneratedTree:
    async def test_the_example_files_are_written(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        assert await _new_project(blnt) == 0

        assert (tmp_cwd / "myapp" / "entities" / "example.py").exists()
        assert (tmp_cwd / "myapp" / "controllers" / "example.py").exists()

    async def test_the_packages_export_the_example(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        assert _read(tmp_cwd, "myapp", "entities", "__init__.py") == (
            "from myapp.entities.example import Base as Base, Example as Example\n"
        )
        assert _read(tmp_cwd, "myapp", "controllers", "__init__.py") == (
            "from myapp.controllers.example import ExampleController as ExampleController\n"
        )

    async def test_the_project_depends_on_the_api_distribution(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        assert '"bolinette-api",' in _read(tmp_cwd, "pyproject.toml")
        assert "ApiExtension()" in _read(tmp_cwd, "myapp", "app.py")

    async def test_a_dry_run_writes_nothing(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        assert await _new_project(blnt, "--dry") == 0

        assert not (tmp_cwd / "myapp").exists()


class TestGeneratedEntity:
    async def test_the_content(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        assert _read(tmp_cwd, "myapp", "entities", "example.py") == (
            "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n\n"
            "from bolinette.data.relational import declarative_base\n\n\n"
            '@declarative_base("default")\n'
            "class Base(DeclarativeBase):\n    pass\n\n\n"
            "class Example(Base):\n"
            '    __tablename__ = "examples"\n\n'
            "    id: Mapped[int] = mapped_column(primary_key=True)\n"
            "    name: Mapped[str]\n"
        )


class TestGeneratedController:
    async def test_it_declares_a_stub_for_every_kind(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        content = _read(tmp_cwd, "myapp", "controllers", "example.py")

        assert '@controller("examples")\nclass ExampleController(ApiController[Example]):' in content
        for kind in ("get_all", "get_one", "create", "update", "patch", "delete"):
            assert f"@autoroute.{kind}" in content

    async def test_the_payload_models(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        content = _read(tmp_cwd, "myapp", "controllers", "example.py")

        assert "class ExamplePayload(BaseModel):\n    name: str\n" in content
        assert "class ExamplePatch(BaseModel):\n    name: str | None = None\n" in content
        assert "class ExampleResponse(BaseModel):\n    id: int\n    name: str\n" in content

    async def test_it_imports_the_generated_entity(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        assert "from myapp.entities import Example" in _read(tmp_cwd, "myapp", "controllers", "example.py")

    async def test_the_generated_modules_are_valid_python(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _new_project(blnt)

        for parts in (("entities", "example.py"), ("controllers", "example.py")):
            compile(_read(tmp_cwd, "myapp", *parts), parts[-1], "exec")
