import getpass

from bolinette_cli import console, paths


def create_user(parser, **options):
    manifest = paths.read_manifest(parser.cwd)
    if manifest is None:
        console.error('No manifest found')
    else:
        from bolinette import db
        from bolinette.exceptions import EntityNotFoundError, ParamConflictError
        from bolinette.services import user_service, role_service

        username = options.get('username')
        email = options.get('email')
        while True:
            password = getpass.getpass('Choose password: ')
            password2 = getpass.getpass('Confirm password: ')
            if password == password2:
                break
            console.error('Passwords don\'t match')
        role_names = options.get('roles')
        with parser.blnt.app.app_context():
            roles = []
            if roles is not None:
                for role_name in [r.strip() for r in role_names.split(',')]:
                    try:
                        roles.append(role_service.get_by_name(role_name))
                    except EntityNotFoundError:
                        console.error(f'Role "{role_name}" does not exist')
                        exit(1)
            try:
                user = user_service.create({
                    'username': username,
                    'password': password,
                    'email': email
                })
                for role in roles:
                    user.roles.append(role)
            except ParamConflictError as ex:
                for message in ex.messages:
                    console.error(f'Conflict: {message.split(":")[1]} already exists')
                exit(1)
            db.session.commit()
