"""Fixtures shared by the data test suite.

Every application is built with the data extension on its own `Cache`, inside a temporary working
directory whose `env/env.toml` declares an in-memory async SQLite database named `default` unless a
test writes its own configuration first.
"""

import os
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest
from escondite import Cache
from soupape import ServiceCollection

from bolinette.core import Bolinette, make_bolinette
from bolinette.core.extensions import Extension
from bolinette.data import DataExtension

type AppFactory = Callable[..., Coroutine[Any, Any, Bolinette]]

DEFAULT_DATABASE = '[[data.databases]]\nname = "default"\nurl = "sqlite+aiosqlite://"\n'


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Turns `@pytest.mark.known_bug("reason")` into a strict xfail, so a fixed bug must drop its marker."""
    for item in items:
        for marker in item.iter_markers("known_bug"):
            reason = marker.kwargs.get("reason") or (marker.args[0] if marker.args else "known bug")
            item.add_marker(pytest.mark.xfail(strict=True, reason=reason))


@pytest.fixture
def cache() -> Cache:
    """A fresh cache, to pass as `cache=` to every decorator used in a test."""
    return Cache()


@pytest.fixture
def tmp_cwd(tmp_path: Path) -> Iterator[Path]:
    """Runs the test with a temporary directory as the current working directory."""
    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(original)


@pytest.fixture
def env_folder(tmp_cwd: Path) -> Path:
    """The `env/` folder of the temporary working directory, created empty."""
    folder = tmp_cwd / "env"
    folder.mkdir()
    return folder


@pytest.fixture
async def make_app(cache: Cache, env_folder: Path) -> AsyncIterator[AppFactory]:
    """Builds applications with the data extension on the test cache and disposes them when the test ends."""
    apps: list[Bolinette] = []

    async def factory(
        extensions: Sequence[Extension] | None = None,
        *,
        services: ServiceCollection | None = None,
        start: bool = True,
    ) -> Bolinette:
        if not (env_folder / "env.toml").exists():
            (env_folder / "env.toml").write_text(DEFAULT_DATABASE)
        blnt = await make_bolinette([DataExtension(), *(extensions or ())], cache=cache, services=services)
        apps.append(blnt)
        if start:
            await blnt.startup()
        return blnt

    yield factory

    for blnt in reversed(apps):
        await blnt.dispose()
