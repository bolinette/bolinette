from bolinette import console
from bolinette.fs import paths, templating


def create_controller(bolinette, **options):
    manifest = paths.read_manifest(bolinette.cwd)
    if manifest is None:
        console.error('No manifest found')
    else:
        module = manifest.get('module')
        path = bolinette.root_path(module)
        origin = bolinette.internal_path('cli', 'files', 'templates')

        model_name = options.get('name')

        params = {
            'module': module,
            'name': model_name
        }

        templating.copy(paths.join(origin, 'controller.py.jinja2'),
                        paths.join(path, 'controllers', f'{model_name}.py'), params)
        paths.append(paths.join(path, 'controllers', '__init__.py'),
                     f'from {module}.controllers.{model_name} import ns as {model_name}_namespace\n')
