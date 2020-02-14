import inflect
import pydash

from bolinette_cli import console, paths, templating
from bolinette_cli.commands.create_controller import create_controller
from bolinette_cli.commands.create_service import create_service


def create_model(parser, **options):
    manifest = paths.read_manifest(parser.cwd)
    if manifest is None:
        console.error('No manifest found')
    else:
        module = manifest.get('module')
        path = parser.root_path(module)
        origin = parser.internal_path('cli', 'files', 'templates')

        model_name = options.get('name')
        class_name = pydash.capitalize(model_name)
        plural_name = inflect.engine().plural(model_name)

        params = {
            'name': model_name,
            'class': class_name,
            'plural': plural_name
        }

        templating.copy(paths.join(origin, 'model.py.jinja2'),
                        paths.join(path, 'models', f'{model_name}.py'), params)
        paths.append(paths.join(path, 'models', '__init__.py'),
                     f'from {module}.models.{model_name} import {class_name}\n')

        if options.get('service', False):
            create_service(parser, name=model_name)

        if options.get('controller', False):
            create_controller(parser, name=model_name)