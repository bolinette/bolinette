import os

import pydash
import inflect

from bolinette.cli import cli_env
from bolinette.cli.utils import copy, join, read_manifest, mkdir


def create_model(**kwargs):
    cwd = cli_env['cwd']
    manifest = read_manifest(cwd)
    module = manifest.get('module')
    path = join(cwd, module)
    origin = join(cli_env['origin'], 'files')

    model = kwargs.get('name').lower()
    kwargs['lower'] = model
    kwargs['class'] = pydash.capitalize(model)
    kwargs['plural'] = inflect.engine().plural(model)

    copy(join(origin, 'model.jinja2'), join(path, 'models', f'{model}.py'), kwargs)
