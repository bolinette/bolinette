from bolinette_cli import console, blnt_version, paths, templating


def create_api(parser, **options):
    manifest = paths.read_manifest(parser.cwd)
    origin = parser.internal_path('files')
    if manifest is not None:
        console.error('Manifest file found, it seems Bolinette has already been initialized!')
    else:
        api_name = options.get('name')
        api_desc = options.get('desc')
        api_module = options.get('module')
        params = {
            'secret_key': paths.random_string(64),
            'jwt_secret_key': paths.random_string(64),
            'module': api_module,
            'name': api_name,
            'desc': api_desc,
            'blnt_version': blnt_version
        }
        templating.render_directory(paths.join(origin, 'api'), parser.cwd, params)
        paths.rename(paths.join(parser.cwd, 'server'), paths.join(parser.cwd, api_module))
