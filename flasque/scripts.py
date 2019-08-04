from flask_script import Command

from flasque import db, transaction, manager
import flasque.models


class InitDb(Command):
    def run(self):
        db.create_all()
        with transaction:
            db.session.add(flasque.models.Role(name='root'))
            db.session.add(flasque.models.Role(name='admin'))


class ResetDb(Command):
    def run(self):
        db.drop_all()
        InitDb().run()


manager.add_command('initdb', InitDb())
manager.add_command('resetdb', ResetDb())
