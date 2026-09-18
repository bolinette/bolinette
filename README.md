# Bolinette

Bolinette is a framework for building applications.
This is its monorepo, which contains the sources of the four packages it is published as.

The `core` package aims to group all [bolinette sub-projects](https://github.com/bolinette) under a single umbrella.
The `data` package is built upon SQLAlchemy and provides a simple way to manage data models and database connections.
The `web` package provides an ASGI web server to build web applications and APIs.
The `api` package binds the `data` and `web` packages together to quickly build REST APIs.

```python
from pydantic import BaseModel

from bolinette.api import ApiController, autoroute
from bolinette.web import controller

from my_app.entities import Example


class ExamplePayload(BaseModel):
    name: str


class ExampleResponse(BaseModel):
    id: int
    name: str


@controller("examples")
class ExampleController(ApiController[Example]):
    @autoroute.get_all
    async def get_all(self) -> list[ExampleResponse]: ...

    @autoroute.create
    async def create(self, payload: ExamplePayload) -> ExampleResponse: ...
```

Six routes over an entity, with the payload and the response staying the types you wrote.

## Getting started

```shell
$ pip install bolinette-api
$ blnt new project
```

`new project` asks which extensions to install, then writes the package, the application factory, the `env` folder and the `tool.bolinette` section of `pyproject.toml`.
With the `api` extension selected it also scaffolds an example entity and its controller.

Bolinette requires Python 3.13 (or newer).

## The packages

| Package | On PyPI | What it brings |
| --- | --- | --- |
| [core](packages/core/README.md) | [bolinette](https://pypi.org/project/bolinette/) | The application, its extensions and configuration, injection, mapping, commands, events and logging |
| [data](packages/data/README.md) | [bolinette-data](https://pypi.org/project/bolinette-data/) | A SQLAlchemy relational layer, with a repository and a service per entity |
| [web](packages/web/README.md) | [bolinette-web](https://pypi.org/project/bolinette-web/) | An ASGI application built from controllers and routes |
| [api](packages/api/README.md) | [bolinette-api](https://pypi.org/project/bolinette-api/) | REST routes generated over a service |

They are all built on the small libraries of the [bolinette organisation](https://github.com/bolinette): [soupape](https://github.com/bolinette/soupape) for dependency injection, [peritype](https://github.com/bolinette/peritype) for runtime type introspection, [muotti](https://github.com/bolinette/muotti) for object mapping, [mirino](https://github.com/bolinette/mirino) for expression paths, [escondite](https://github.com/bolinette/escondite) and [hafersack](https://github.com/bolinette/hafersack) for the cache and metadata the decorators write to.

Each of those is useful on its own, outside any framework.

## Development

The monorepo is a [uv](https://docs.astral.sh/uv/) workspace.
Each directory under `packages/` is a separately published distribution sharing the `bolinette` namespace package, and their versions move together with exact pins between them.

```shell
uv sync --all-groups           # install every package editable, with dev and test tools
uv run python -m pytest        # run the tests
uv run ruff check packages tests
uv run pyright
uv build --all-packages        # build one wheel and sdist per package into dist/
```

Ruff, pyright and pytest all run from the root, over `packages/` and `tests/`.

## License

Bolinette is released under the MIT license, see [LICENSE.txt](LICENSE.txt).
