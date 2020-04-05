from datetime import datetime

from bolinette import transaction, db, env
from bolinette.services import role_service, user_service

from example.services import book_service, person_service


@db.engine.seeder
async def role_seeder():
    with transaction:
        await role_service.create({'name': 'root'})
        await role_service.create({'name': 'admin'})


@db.engine.seeder
async def dev_user_seeder():
    if env['PROFILE'] == 'development':
        with transaction:
            root = await role_service.get_by_name('root')
            admin = await role_service.get_by_name('admin')
            root_usr = await user_service.create({
                'username': 'root',
                'password': 'root',
                'email': f'root@localhost'
            })
            root_usr.roles.append(root)
            root_usr.roles.append(admin)

            dev0 = await role_service.create({'name': 'dev0'})
            dev1 = await role_service.create({'name': 'dev1'})
            dev2 = await role_service.create({'name': 'dev2'})
            roles = [dev0, dev1, dev2]

            for i in range(10):
                user = await user_service.create({
                    'username': f'user_{i}',
                    'password': 'test',
                    'email': f'user{i}@test.com'
                })
                user.roles.append(roles[i % 3])
                user.roles.append(roles[(i + 1) % 3])


@db.engine.seeder
async def seed_app():
    if env['PROFILE'] == 'development':
        with transaction:
            p1 = await person_service.create({'first_name': 'J.R.R.', 'last_name': 'Tolkien'})
        with transaction:
            user = await user_service.get_by_username('root')
            await book_service.create(
                {'name': 'The Fellowship of the Ring', 'pages': 678, 'author_id': p1.id,
                 'price': 23.45, 'publication_date': datetime(1954, 7, 29)}, current_user=user)
            await book_service.create(
                {'name': 'The Two Towers', 'pages': 612, 'author_id': p1.id,
                 'price': 24.58, 'publication_date': datetime(1954, 11, 11)}, current_user=user)
            await book_service.create(
                {'name': 'The Return of the King', 'pages': 745, 'author_id': p1.id,
                 'price': 25.7, 'publication_date': datetime(1955, 10, 20)}, current_user=user)
