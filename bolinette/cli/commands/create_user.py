import getpass

from bolinette import console, db
from bolinette.exceptions import EntityNotFoundError, ParamConflictError
from bolinette.fs import paths
from bolinette.services import user_service, role_service


def create_user(bolinette, **options):
    manifest = paths.read_manifest(bolinette.cwd)
    if manifest is None:
        console.error('No manifest found')
    else:
        username = options.get('username')
        email = options.get('email')
        while True:
            password = getpass.getpass('Choose password: ')
            password2 = getpass.getpass('Confirm password: ')
            if password == password2:
                break
            console.error('Passwords don\'t match')
        role_names = options.get('roles')
        with bolinette.app.app_context():
            roles = []
            if roles is not None:
                for role_name in [r.strip() for r in role_names.split(',')]:
                    try:
                        roles.append(role_service.get_by_name(role_name))
                    except EntityNotFoundError:
                        console.error(f'Role "{role_name}" does not exist')
                        exit(1)
            try:
                user_service.create({'username': username, 'password': password,
                                     'roles': roles, 'email': email})
            except ParamConflictError as ex:
                for message in ex.messages:
                    console.error(f'Conflict: {message.split(":")[1]} already exists')
                exit(1)
            db.session.commit()
