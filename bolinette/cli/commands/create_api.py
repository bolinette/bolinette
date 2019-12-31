from bolinette import console, version
from bolinette.cli import cli_env, utils


def create_api(**options):
    cwd = cli_env['cwd']
    origin = utils.join(cli_env['origin'], 'files')
    manifest = utils.read_manifest(cwd)
    if manifest is not None:
        console.error('Manifest file found, it seems Bolinette has already been initialized!')
    else:
        api_name = options.get('name')
        api_desc = options.get('desc')
        api_module = options.get('module')
        params = {
            'secret_key': utils.random_string(64),
            'jwt_secret_key': utils.random_string(64),
            'module': api_module,
            'name': api_name,
            'desc': api_desc,
            'blnt_version': version
        }
        utils.render_directory(utils.join(origin, 'api'), cwd, params)
        utils.rename(utils.join(cwd, 'server'), utils.join(cwd, api_module))
