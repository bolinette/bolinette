from bolinette import transaction, db
from bolinette.database import run_seeders


def init_db(bolinette, **options):
    seed = options.get('seed', False)
    with bolinette.app.app_context():
        db.drop_all()
        db.create_all()
        if seed:
            with transaction:
                run_seeders()
