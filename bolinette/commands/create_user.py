import getpass

import bolinette
from bolinette import Console
from bolinette.blnt import Transaction
from bolinette.decorators import command
from bolinette.exceptions import ParamConflictError, EntityNotFoundError, APIError, APIErrors


@command('create_user', 'Add a user to the database')
@command.argument('argument', 'username', summary='The new user\'s username')
@command.argument('argument', 'email', summary='The new user\'s email')
@command.argument('option', 'roles', flag='r', summary='The user\'s roles, comma separated')
async def create_user(blnt: 'bolinette.Bolinette', username: str, email: str, roles: str = None):
    console = Console()
    user_service = blnt.context.service('user')
    role_service = blnt.context.service('role')
    while True:
        password = getpass.getpass('Choose password: ')
        password2 = getpass.getpass('Confirm password: ')
        if password == password2:
            break
        console.error('Passwords don\'t match')
    async with Transaction(blnt.context, print_error=False, propagate_error=False):
        user_roles = []
        if roles is not None:
            for role_name in [r.strip() for r in roles.split(',')]:
                try:
                    user_roles.append(await role_service.get_by_name(role_name))
                except EntityNotFoundError:
                    console.error(f'Role "{role_name}" does not exist')
                    exit(1)
        try:
            user = await user_service.create({
                'username': username,
                'password': password,
                'email': email
            })
            for role in user_roles:
                user.roles.append(role)
        except (APIError, APIErrors) as ex:
            if isinstance(ex, APIError):
                errors = [ex]
            else:
                errors = ex.errors
            for err in [err for err in errors if isinstance(err, ParamConflictError)]:
                console.error(f'Conflict: {err.message.split(":")[1]} already exists')
            exit(1)
