# Introduction

## What is bolinette?

Bolinette is a complete asynchronous Python web framework based on [aiohttp](https://docs.aiohttp.org/en/stable/).
It provides an easy out-of-the-box experience to help you build complex web APIs with a minimum of work.
Bolinette can scale up from a small project to a complex application.

## Getting started

Install the [Bolinette package](https://pypi.org/project/Bolinette/) with pip.

```shell
$ pip install bolinette
```

Don't forget to use a virtual environment for better package version management.

```shell
$ python -m venv venv && source venv/bin/activate && pip install -U pip && pip install bolinette
```

Now you can create a new Bolinette app.
Then, everything is injected through decorators.
Use the following code to set up the base of your Bolinette app.

```python
# server.py
from bolinette import Bolinette

blnt = Bolinette()

if __name__ == '__main__':
    blnt.run_command()
```

Then use one of the internal commands.

```shell
$ python server.py run_server
```

You can find a complete list of commands [here](commands.md).
This one runs the web app, listening by default on port 5000.

You can just run the web app like this.

```python
from bolinette import Bolinette

blnt = Bolinette()
blnt.run()
```

## What's next?

To add some custom logic to your application, the next steps are:
- Create a [model](models.md), to store data in the [database](database.md)
- Create a [service](services.md), to add your custom logic
- Create a [controller](controllers.md), the entrypoint of your new service
