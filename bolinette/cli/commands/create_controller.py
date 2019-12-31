from bolinette.cli import cli_env, utils


def create_controller(**options):
    cwd = cli_env['cwd']
    origin = utils.join(cli_env['origin'], 'files', 'templates')
