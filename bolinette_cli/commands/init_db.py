from bolinette import transaction, db
from bolinette.database import run_seeders


def init_db(parser, **options):
    seed = options.get('seed', False)
    with parser.blnt.app.app_context():
        db.drop_all()
        db.create_all()
        if seed:
            with transaction:
                run_seeders()
