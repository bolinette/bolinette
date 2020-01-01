import pydash

from bolinette import console
from bolinette.cli import cli_env, utils
from bolinette.cli.commands.create_controller import create_controller


def create_service(**options):
    cwd = cli_env['cwd']
    manifest = utils.read_manifest(cwd)
    if manifest is None:
        console.error('No manifest found')
    else:
        module = manifest.get('module')
        path = utils.join(cwd, module)
        origin = utils.join(cli_env['origin'], 'files', 'templates')

        model_name = options.get('name')
        class_name = pydash.capitalize(model_name)

        params = {
            'module': module,
            'name': model_name,
            'class': class_name
        }

        utils.copy(utils.join(origin, 'service.py.jinja2'),
                   utils.join(path, 'services', f'{model_name}.py'), params)
        utils.append(utils.join(path, 'services', '__init__.py'),
                     f'from {module}.services.{model_name} import {model_name}_service\n')

        if options.get('controller', False):
            create_controller(name=model_name)
