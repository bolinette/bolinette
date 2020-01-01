import inflect
import pydash

from bolinette import console
from bolinette.cli import cli_env, utils
from bolinette.cli.commands.create_controller import create_controller
from bolinette.cli.commands.create_service import create_service


def create_model(**options):
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
        plural_name = inflect.engine().plural(model_name)

        params = {
            'name': model_name,
            'class': class_name,
            'plural': plural_name
        }

        utils.copy(utils.join(origin, 'model.py.jinja2'),
                   utils.join(path, 'models', f'{model_name}.py'), params)
        utils.append(utils.join(path, 'models', '__init__.py'),
                     f'from {module}.models.{model_name} import {class_name}\n')

        if options.get('service', False):
            create_service(name=model_name)

        if options.get('controller', False):
            create_controller(name=model_name)
