# Bolinette

Bolinette is a Python web framework built on top of [aiohttp](https://github.com/aio-libs/aiohttp).

[Read the complete docs here!](https://docs.bolinette.org/)

## Install

### Prerequisites

Bolinette requires Python 3.10.
Get it from the [official sources](https://www.python.org/downloads/).
Be sure to install the pip and virtualenv extensions.

### Create your project folder

```sh
mkdir my-project && cd my-project
```

### Install Bolinette

With a virtual environment:
```sh
python3.9 -m venv venv && source venv/bin/activate && pip install pip --upgrade && pip install bolinette
```

Globally, with admin rights:
```sh
pip install pip --upgrade && pip install bolinette
```

## Use the Bolinette CLI

### Initialize your project

```sh
blnt init app my_project
```

You will then be asked a few questions about the new project.

### Useful commands

```sh
blnt run server //runs the development server
blnt init db [-s] //creates tables in database [and runs seeders]
blnt new [model|service|controller] //creates new files from generic templates
```

Find all available commands with `blnt -h`.
