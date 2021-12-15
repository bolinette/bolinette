import random
from datetime import datetime

from bolinette import abc, core
from bolinette.decorators import seeder
from bolinette.defaults.services import RoleService, UserService

from example.services import BookService, PersonService, LibraryService, TagService, LabelService


@seeder
async def role_seeder(context: abc.Context):
    role_service: RoleService = context.inject.require(RoleService, immediate=True)
    async with core.Transaction(context):
        await role_service.create({'name': 'root'})
        await role_service.create({'name': 'admin'})


@seeder
async def dev_user_seeder(context: abc.Context):
    rng = random.Random()
    first_names = ['Bob', 'Jack', 'Bill', 'Joe']
    last_names = ['Smith', 'Johnson', 'Jones', 'Miller']
    if context.env['profile'] == 'development':
        role_service: RoleService = context.inject.require(RoleService, immediate=True)
        user_service: UserService = context.inject.require(UserService, immediate=True)
        async with core.Transaction(context):
            root = await role_service.get_by_name('root')
            admin = await role_service.get_by_name('admin')
            root_usr = await user_service.create({
                'username': 'root',
                'password': 'root',
                'email': 'root@localhost',
                'first_name': rng.choice(first_names),
                'last_name': rng.choice(last_names),
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
                    'email': f'user{i}@test.com',
                    'first_name': rng.choice(first_names),
                    'last_name': rng.choice(last_names),
                })
                user.roles.append(roles[i % 3])
                user.roles.append(roles[(i + 1) % 3])


@seeder
async def book_seeder(context: abc.Context):
    if context.env['profile'] == 'development':
        user_service = context.inject.require(UserService, immediate=True)
        person_service = context.inject.require(PersonService, immediate=True)
        book_service = context.inject.require(BookService, immediate=True)
        async with core.Transaction(context):
            user = await user_service.get_by_username('root')
            p1 = await person_service.create(
                {'uid': 'JRR_TOLKIEN', 'first_name': 'J.R.R.', 'last_name': 'Tolkien'}, current_user=user)
            await book_service.create(
                {'uid': 'LOTR_1', 'name': 'The Fellowship of the Ring', 'pages': 678, 'author': p1,
                 'price': 23.45, 'publication_date': datetime(1954, 7, 29)}, current_user=user)
            await book_service.create(
                {'uid': 'LOTR_2', 'name': 'The Two Towers', 'pages': 612, 'author': p1,
                 'price': 24.58, 'publication_date': datetime(1954, 11, 11)}, current_user=user)
            await book_service.create(
                {'uid': 'LOTR_3', 'name': 'The Return of the King', 'pages': 745, 'author': p1,
                 'price': 25.7, 'publication_date': datetime(1955, 10, 20)}, current_user=user)


@seeder
async def library_seeder(context: abc.Context):
    if context.env['profile'] == 'development':
        library_service = context.inject.require(LibraryService, immediate=True)
        async with core.Transaction(context):
            await library_service.create({
                'key': 'dwntwn_bks', 'name': 'Downtown books'
            })
            await library_service.create({
                'key': 'knlg', 'name': 'Unlimited Knowledge'
            })
            await library_service.create({
                'key': 'sph_bks', 'name': 'Sophie\'s books'
            })


@seeder
async def tag_seeder(context: abc.Context):
    if context.env['profile'] == 'development':
        tag_service = context.inject.require(TagService, immediate=True)
        label_service = context.inject.require(LabelService, immediate=True)
        async with core.Transaction(context):
            t1 = await tag_service.create({'name': 't1'})
            t2 = await tag_service.create({'name': 't2'})
            t11 = await tag_service.create({'name': 't11', 'parent': t1})
            await tag_service.create({'name': 't111', 'parent': t11})
            await tag_service.create({'name': 't21', 'parent': t2})

            await label_service.create({'name': 'l11', 'tag': t1, 'id': 1})
            await label_service.create({'name': 'l12', 'tag': t1, 'id': 2})
            await label_service.create({'name': 'l21', 'tag': t2, 'id': 1})
