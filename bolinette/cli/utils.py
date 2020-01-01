import importlib
import os
import random
import re
import string
import subprocess
import sys

import jinja2
import yaml


def mkdir(path):
    os.makedirs(path)


def rename(path, new_path):
    os.rename(path, new_path)


def join(*args):
    return os.path.join(*args)


def write(path, content):
    with open(path, mode='w+') as file:
        file.write(content)


def append(path, content):
    with open(path, mode='a+') as file:
        file.write(content)


def render(path, params):
    template_path, template_name = os.path.split(path)
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=template_path), keep_trailing_newline=True)
    template = jinja_env.get_template(template_name)
    return template.render(**params)


def copy(origin, dest, params):
    content = render(origin, params)
    write(re.sub(r'\.jinja2$', '', dest), content)


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


def pickup_blnt(cwd):
    manifest = read_manifest(cwd)
    if manifest is not None:
        if cwd not in sys.path:
            sys.path = [cwd] + sys.path
        module = importlib.import_module(manifest.get('module'))
        blnt = getattr(module, 'blnt', None)
        return blnt
    return None
