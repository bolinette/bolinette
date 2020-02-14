import os
import random
import string

import yaml


def cwd():
    return os.getcwd()


def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


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


def write(path, content, mode='w+'):
    with open(path, mode=mode) as file:
        file.write(content)


def append(path, content):
    write(path, content, mode='a+')


def read_manifest(path):
    try:
        with open(join(path, 'manifest.blnt.yml')) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None
