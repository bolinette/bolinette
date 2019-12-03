import os
import random
import string

import yaml
from jinja2 import Template


def mkdir(path):
    os.makedirs(path)


def join(*args):
    return os.path.join(*args)


def write(path, content):
    with open(path, mode='w+') as file:
        file.write(content)


def render(path, params):
    with open(path) as file:
        template = Template(file.read())
        return template.render(**params)


def copy(origin, dest, params):
    content = render(origin, params)
    write(dest, content)


def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def read_manifest(path):
    with open(join(path, 'manifest.bolinette.yaml')) as f:
        return yaml.safe_load(f)
