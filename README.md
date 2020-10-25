# Bolinette

Bolinette is a Python web framework built on top of [aiohttp](https://github.com/aio-libs/aiohttp)

## Install

### Prerequisites

Bolinette requires Python 3.9. Get it from the [official sources](https://www.python.org/downloads/). Be sure to
install the pip and virtualenv extensions.

### Create your project folder

```shell script
mkdir my_project && cd my_project
```

### Install Bolinette

With a virtual environment:
```shell script
python3.9 -m venv venv && source venv/bin/activate && pip install pip --upgrade && pip install bolinette
```

Globally, with admin rights:
```shell script
pip install pip --upgrade && pip install bolinette
```

## Use the Bolinette CLI

*The CLI is work in progress.*

## Internal API

- [Cache](./docs/cache.md)
- [Exceptions](./docs/exceptions.md)
- [Environment](./docs/environment.md)
  - [Profile](./docs/environment.md#profile)
  - [Init variables](./docs/environment.md#init-variables)
  - [Environment variables](./docs/environment.md#environment-variables)
- [Init function](./docs/init.md)
- [Context](./docs/context.md)
  - [app](./docs/context.md#aiohttp-application)
  - [env](./docs/context.md#environment)
- [Models](./docs/models.md)
