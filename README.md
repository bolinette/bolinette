# Bolinette

This is the Bolinette monorepo, which contains the sources of the bolinette packages.

Bolinette is a framework for building applications.
The `core` package aims to group all [bolinette sub-projects](https://github.com/bolinette) under a single umbrella.
The `data` package is built upon SQALAlchemy and provides a simple way to manage data models and database connections.
The `web` package provides an ASGI web server to build web applications and APIs.
The `api` package binds the `data` and `web` packages together to quickly build REST APIs.

# [core](packages/core/README.md)

# [data](packages/data/README.md)

`data` uses SQLAlchemy to create a standard way to manage data models and database connections.
CRUD operations are handled by the `Repository`, and the `Service` creates a layer between the repository and your application to handle business logic.
`data` is uses [soupape](https://github.com/bolinette/soupape) to inject default implementations and allow you to override them with your own.

```python
TODO example
```
