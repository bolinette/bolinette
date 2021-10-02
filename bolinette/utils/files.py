from typing import Any

import jinja2
import yaml

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


def read_manifest(path, *, params: dict[str, Any] = None):
    try:
        with open(paths.join(path, 'manifest.blnt.yaml')) as f:
            raw = f.read()
            if params is not None:
                for param in params:
                    raw = raw.replace(f'__{param}__', params[param])
            return yaml.safe_load(raw)
    except FileNotFoundError:
        return None


def render_template(workdir: str, path: str, params: dict[str, Any]):
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=workdir),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True
    )
    return jinja_env.get_template(path).render(**params)


def render_string(string: str, params: dict[str, Any]):
    jinja_env = jinja2.Environment(
        loader=jinja2.BaseLoader,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True
    )
    return jinja_env.from_string(string).render(**params)
