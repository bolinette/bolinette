from bolinette.cli import cli_env, utils


def create_api(**kwargs):
    cwd = cli_env['cwd']
    origin = utils.join(cli_env['origin'], 'files')
    params = {
        'secret_key': utils.random_string(64),
        'jwt_secret_key': utils.random_string(64),
    }
    utils.render_directory(utils.join(origin, 'api'), cwd, params)
