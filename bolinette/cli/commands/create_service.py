import pydash

from bolinette import console
from bolinette.cli.commands.create_controller import create_controller
from bolinette.fs import templating, paths


def create_service(bolinette, **options):
    manifest = paths.read_manifest(bolinette.cwd)
    if manifest is None:
        console.error('No manifest found')
    else:
        module = manifest.get('module')
        path = bolinette.root_path(module)
        origin = bolinette.internal_path('cli', 'files', 'templates')

        model_name = options.get('name')
        class_name = pydash.capitalize(model_name)

        params = {
            'module': module,
            'name': model_name,
            'class': class_name
        }

        templating.copy(paths.join(origin, 'service.py.jinja2'),
                        paths.join(path, 'services', f'{model_name}.py'), params)
        paths.append(paths.join(path, 'services', '__init__.py'),
                     f'from {module}.services.{model_name} import {model_name}_service\n')

        if options.get('controller', False):
            create_controller(bolinette, name=model_name)
