# bolinette-api

The Bolinette api extension: REST routes generated over a `Service[Entity]`.

A controller declares the usual routes as empty stubs, typed by their own signature, and the extension replaces each one with a real route once it knows the entity.
The payload and the response stay yours: they are the types written on the stub, so nothing is generated behind your back.

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

## Installation

```shell
$ pip install bolinette-api  # or use your preferred package manager
```

## Requirements

Bolinette-api requires Python 3.13 (or newer), and depends on [bolinette](https://pypi.org/project/bolinette/), [bolinette-data](https://pypi.org/project/bolinette-data/) and [bolinette-web](https://pypi.org/project/bolinette-web/).
It is the package that binds the other two together, so it is only worth installing when an application has both entities and routes.

## What the api extension does

- **Six autoroutes** — `get_all`, `get_one`, `create`, `update`, `patch` and `delete`, each mapping to a `Service` call.
- **Paths from the primary key** — a route addressing one entity follows the key columns, so a composite key becomes several segments.
- **Your types, not generated ones** — the stub's parameter is what the body is mapped onto, and its return type is what the entity is mapped to on the way out.
  Anything the mapper has a protocol for works, which includes dataclasses and `TypedDict`s alongside pydantic models.
- **The service without asking** — `ApiController[Entity]` receives its `Service[Entity]` and the mapper in its post_init.
- **Hand-written routes alongside** — an `ApiController` is a `Controller`, so a route the generator cannot express is written next to the stubs with the ordinary web decorators.
- **Sensible defaults** — `create` and `update` flush before mapping the response, so a generated primary key reaches the client, and a missing entity becomes a 404 carrying `api.entity.not_found`.

`blnt new project` scaffolds an example entity and its controller when this extension is selected, which is the shortest way to see the whole shape at once.

## License

Bolinette is released under the MIT license, see [LICENSE.txt](LICENSE.txt).
