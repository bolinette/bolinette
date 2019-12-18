import os
import random
import string
import subprocess
import re

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
    write(re.sub(r'.jinja2$', '', dest), content)


def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def read_manifest(path):
    try:
        with open(join(path, 'manifest.blnt.yml')) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def run_shell_command(command, args, out_fn):
    process = subprocess.Popen([command, *args], stdout=subprocess.PIPE)
    for line in iter(process.stdout.readline, ''):
        if len(line) > 0:
            out_fn(line.rstrip().decode('utf-8'))
        else:
            break


def render_directory(origin, dest, params):
    if not os.path.exists(dest):
        mkdir(dest)
    for f in os.listdir(origin):
        if os.path.isdir(join(origin, f)):
            render_directory(join(origin, f), join(dest, f), params)
        if os.path.isfile(join(origin, f)):
            copy(join(origin, f), join(dest, f), params)
