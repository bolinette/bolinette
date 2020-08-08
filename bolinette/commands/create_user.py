import getpass

from bolinette_common import console

import bolinette
from bolinette.commands import command
from bolinette.exceptions import ParamConflictError, EntityNotFoundError


@command('create_user')
def create_user(blnt: 'bolinette.Bolinette', *, username, email, roles):
    user_service = blnt.context.service('user')
    role_service = blnt.context.service('role')
    while True:
        password = getpass.getpass('Choose password: ')
        password2 = getpass.getpass('Confirm password: ')
        if password == password2:
            break
        console.error('Passwords don\'t match')
    with blnt.app.app_context():
        user_roles = []
        if user_roles is not None:
            for role_name in [r.strip() for r in roles.split(',')]:
                try:
                    user_roles.append(role_service.get_by_name(role_name))
                except EntityNotFoundError:
                    console.error(f'Role "{role_name}" does not exist')
                    exit(1)
        try:
            user = user_service.create({
                'username': username,
                'password': password,
                'email': email
            })
            for role in user_roles:
                user.roles.append(role)
        except ParamConflictError as ex:
            for message in ex.messages:
                console.error(f'Conflict: {message.split(":")[1]} already exists')
            exit(1)
        blnt.context.db.session.commit()
