# bolinette-web

The Bolinette web extension: an ASGI application built from controllers and routes.

A controller is a class, a route is one of its methods, and everything the method needs is injected, including the path parameters, the query string and the request payload.
Each request gets its own injector scope, so a scoped service lives exactly as long as the request that asked for it.

```python
from typing import Annotated

from bolinette.web import Controller, Payload, PathParam, controller, get, post


@controller("items")
class ItemController(Controller):
    @get("{item_id}")
    async def one(self, item_id: Annotated[int, PathParam()]) -> ItemResponse: ...

    @post("")
    async def create(self, payload: Annotated[ItemPayload, Payload()]) -> ItemResponse: ...
```

## Installation

```shell
$ pip install bolinette-web          # or use your preferred package manager
$ pip install bolinette-web[auth]    # with the bundled JWT provider
```

## Requirements

Bolinette-web requires Python 3.13 (or newer), and depends on [bolinette](https://pypi.org/project/bolinette/).
The `auth` extra adds [pyjwt](https://pypi.org/project/PyJWT/) with its cryptography backend, and is only needed for the bundled authentication provider.

## What the web extension does

- **Controllers and routes** — `controller` mounts a class on a path, and `get`, `post`, `put`, `patch` and `delete` mount its methods under it.
  A path segment can carry a regular expression, written after a colon.
- **Injected request data** — `PathParam`, `QueryParam` and `Payload` mark the parameters read from the request; anything unannotated is a service.
  Each falls back from the request value to the default, then to `None` if the type allows it, then to a `BadRequestError`.
- **Typed responses** — a route returns whatever it wants, encoded as JSON through the core mapper.
- **Middlewares** — `with_middleware` wraps a controller or a single route, `without_middleware` takes one off a route that inherited it.
- **Authentication** — the `auth` extra ships a JWT provider, enabled through `WebExtension(blnt_auth=...)`, with `blnt auth new rsa` to generate its keys.
- **WebSockets** — handlers declared like routes, with the same injection, and subscriptions released when the connection closes.
- **A server, not bundled** — `create_asgi_app` turns the application factory into the callable uvicorn or hypercorn runs.

```python
from bolinette.web import create_asgi_app

from my_app import make_bolinette

app = create_asgi_app(make_bolinette)
```

## License

Bolinette is released under the MIT license, see [LICENSE.txt](LICENSE.txt).
