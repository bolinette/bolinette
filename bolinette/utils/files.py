from os import PathLike

import jinja2
import yaml
from jinja2 import TemplateNotFound

from bolinette.exceptions import InternalError
from bolinette.utils import paths


def write(path, content, mode='w+'):
    with open(path, mode=mode) as file:
        file.write(content)


def append(path, content):
    write(path, content, mode='a+')


def read_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def read_requirements(path):
    try:
        with open(paths.join(path, 'requirements.txt')) as f:
            return list(filter(lambda r: len(r), f.read().split('\n')))
    except FileNotFoundError:
        return []


def read_manifest(path):
    try:
        with open(paths.join(path, 'manifest.blnt.yml')) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def render_template(workdir: PathLike, path: PathLike, params):
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=workdir),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True
    )
    return jinja_env.get_template(path).render(**params)
