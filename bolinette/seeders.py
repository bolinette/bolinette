from bolinette import env, seeder, transaction
from bolinette.services import role_service, user_service


@seeder
def role_seeder():
    with transaction:
        role_service.create({'name': 'root'})
        role_service.create({'name': 'admin'})


@seeder
def dev_user_seeder():
    if env['PROFILE'] == 'development':
        with transaction:
            root = role_service.get_by_name('root')
            admin = role_service.get_by_name('admin')
            root_usr = user_service.create({
                'username': 'root',
                'password': 'root',
                'email': f'root@localhost'
            })
            root_usr.roles.append(root)
            root_usr.roles.append(admin)

            dev0 = role_service.create({'name': 'dev0'})
            dev1 = role_service.create({'name': 'dev1'})
            dev2 = role_service.create({'name': 'dev2'})
            roles = [dev0, dev1, dev2]

            for i in range(10):
                user = user_service.create({
                    'username': f'user_{i}',
                    'password': 'test',
                    'email': f'user{i}@test.com'
                })
                user.roles.append(roles[i % 3])
                user.roles.append(roles[(i + 1) % 3])
