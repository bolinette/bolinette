# bolinette

Bolinette is a framework for building Python applications.
This package is its core: it builds the application, loads the extensions, reads the configuration, and gives every other package the injection, mapping, commands, events and logging they are written against.

Core is useful on its own, for an application that is not a web server: a command line tool, a worker, a batch job.
The relational layer, the ASGI server and the REST routes live in [bolinette-data](https://pypi.org/project/bolinette-data/), [bolinette-web](https://pypi.org/project/bolinette-web/) and [bolinette-api](https://pypi.org/project/bolinette-api/).

```python
from bolinette import core


async def make_bolinette() -> core.Bolinette:
    return await core.make_bolinette(extensions=[core.CoreExtension()])
```

## Installation

```shell
$ pip install bolinette  # or use your preferred package manager
```

The `blnt new project` command scaffolds a project, asks which extensions to install, and writes the package, the application factory and the `env` folder.

## Requirements

Bolinette requires Python 3.13 (or newer).
The core package depends on [soupape](https://pypi.org/project/soupape/) for dependency injection, [peritype](https://pypi.org/project/peritype/) for runtime type introspection, [muotti](https://pypi.org/project/muotti/) for object mapping, [mirino](https://pypi.org/project/mirino/) for the paths errors are reported on, [escondite](https://pypi.org/project/escondite/) and [hafersack](https://pypi.org/project/hafersack/) for the cache and metadata its decorators write to, and on [pydantic](https://pypi.org/project/pydantic/).

## What the core does

- **Application lifecycle** — `make_bolinette` builds the application from a list of extensions.
  Nothing runs until `startup()` is awaited, and `dispose()` closes the injector.
- **Extensions** — a class with a name, its dependencies and a `register_services` method.
  Packages advertise theirs through the `bolinette.extensions` entry point group, which the scaffolding reads.
- **Configuration** — pydantic sections decorated with `config_section`, injected as `ConfigSection[T]`.
  Layered over `env/` files, per profile, with environment variables underneath.
- **Dependency injection** — every service, route and command has its parameters resolved by [soupape](https://pypi.org/project/soupape/).
- **Object mapping** — payloads and responses go through a [muotti](https://pypi.org/project/muotti/) mapper, reporting the field path a conversion failed on.
- **Commands** — async functions registered with `command`, their parameters annotated as arguments or options, run by `blnt`.
- **Events** — listeners for the initialized, started, stopped and error events of the application.
- **Logging** — `Logger[T]` is a standard logger named after the type it is injected into, configured by the core section.
- **Testing** — `Mock` builds a stub for any injectable type and records the calls made on it.

Bolinette is fully typed and checked in Pyright's strict mode.

## License

Bolinette is released under the MIT license, see [LICENSE.txt](LICENSE.txt).
