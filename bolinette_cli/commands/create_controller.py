from bolinette_cli import console, paths, templating


def create_controller(parser, **options):
    manifest = paths.read_manifest(parser.cwd)
    if manifest is None:
        console.error('No manifest found')
    else:
        module = manifest.get('module')
        path = parser.root_path(module)
        origin = parser.internal_path('cli', 'files', 'templates')

        model_name = options.get('name')

        params = {
            'module': module,
            'name': model_name
        }

        templating.copy(paths.join(origin, 'controller.py.jinja2'),
                        paths.join(path, 'controllers', f'{model_name}.py'), params)
        paths.append(paths.join(path, 'controllers', '__init__.py'),
                     f'from {module}.controllers.{model_name} import ns as {model_name}_namespace\n')
