from bolinette import transaction, db
from bolinette.cli import cli_env
from bolinette.database import run_seeders


def init_db(**options):
    blnt = cli_env['bolinette']
    seed = options.get('seed', False)
    with blnt.app.app_context():
        db.drop_all()
        db.create_all()
        if seed:
            with transaction:
                run_seeders()
