# Bolinette

Bolinette is a framework built around the Flask micro-framework.

## Install

### Prerequisites

Bolinette requires Python 3.8. Get it from the [official sources](https://www.python.org/downloads/). Be sure to
install the pip and virtualenv extensions.

### Create your project folder

```shell script
mkdir my_project && cd my_project
```

### Install Bolinette

With a virtual environment:
```shell script
python3.8 -m venv venv && source venv/bin/activate && pip install pip --upgrade && pip install bolinette
```

Globally, with admin rights:
```shell script
pip install pip --upgrade && pip install bolinette
```

## Use the Bolinette CLI

Whether you use the virtualenv or global method, you can use the CLI with the `blnt` command. If you are using
a virtualenv, be sure to activate it before using the CLI.

First, you need to initialize your Bolinette app.

```shell script
blnt init app
```

This will create all the files you need to run a default Bolinette server and web app. This creates the secrets keys
for the development env, inside `instance/development.local.env`.

```shell script
blnt init db --seed
```

This command initializes the database. By default, Bolinette uses a SQLITE file, located in the `instance` folder.
This file is named `env.db`, replacing `env` by the current execution environment, like `development`, `test` or
`production`. You can use another database system by overriding the DBMS environment key.

## Run the server

```shell script
blnt run server
```

This is the development Flask server, not intended for production. For production hosting, you can use
[Gunicorn](https://gunicorn.org/).

```shell script
gunicorn server
```

By default, the main API package is `server`. Gunicorn will load the `application` attribute inside
`server/__init__.py`.
