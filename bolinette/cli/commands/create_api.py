from bolinette import console, version
from bolinette.fs import paths, templating


def create_api(bolinette, **options):
    manifest = paths.read_manifest(bolinette.cwd)
    origin = bolinette.internal_path('cli', 'files')
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
            'blnt_version': version
        }
        templating.render_directory(paths.join(origin, 'api'), bolinette.cwd, params)
        paths.rename(paths.join(bolinette.cwd, 'server'), paths.join(bolinette.cwd, api_module))
