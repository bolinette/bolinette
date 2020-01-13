import os
import re

import yaml


def cwd():
    return os.getcwd()


def mkdir(path):
    os.makedirs(path)


def rename(path, new_path):
    os.rename(path, new_path)


def join(*args):
    return os.path.join(*args)


def dirname(path):
    return os.path.dirname(os.path.realpath(path))


def split(path):
    return os.path.split(path)


def write(path, content):
    with open(path, mode='w+') as file:
        file.write(content)


def append(path, content):
    with open(path, mode='a+') as file:
        file.write(content)


def copy(origin, dest, params):
    content = render(origin, params)
    write(re.sub(r'\.jinja2$', '', dest), content)


def read_manifest(path):
    try:
        with open(join(path, 'manifest.blnt.yml')) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None
