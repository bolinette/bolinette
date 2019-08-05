from flask_script import Command

from bolinette import db, transaction
import bolinette.models


class InitDb(Command):
    def run(self):
        db.create_all()
        with transaction:
            db.session.add(bolinette.models.Role(name='root'))
            db.session.add(bolinette.models.Role(name='admin'))


class ResetDb(Command):
    def run(self):
        db.drop_all()
        InitDb().run()


def init_commands(manager):
    manager.add_command('initdb', InitDb())
    manager.add_command('resetdb', ResetDb())
