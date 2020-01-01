from bolinette import console
from bolinette.cli import cli_env, utils


def create_controller(**options):
    cwd = cli_env['cwd']
    manifest = utils.read_manifest(cwd)
    if manifest is None:
        console.error('No manifest found')
    else:
        module = manifest.get('module')
        path = utils.join(cwd, module)
        origin = utils.join(cli_env['origin'], 'files', 'templates')

        model_name = options.get('name')

        params = {
            'module': module,
            'name': model_name
        }

        utils.copy(utils.join(origin, 'controller.py.jinja2'),
                   utils.join(path, 'controllers', f'{model_name}.py'), params)
        utils.append(utils.join(path, 'controllers', '__init__.py'),
                     f'from {module}.controllers.{model_name} import ns as {model_name}_namespace\n')
