import sys
from typing import Any

from bolinette import blnt, Console
from bolinette.utils import files, paths
from bolinette.decorators import command


def _create_file(console: Console, *,
                 source_dir: str, source_template: str, dest_dir: str, dest_file: str,
                 params: dict[str, Any]):
    if not paths.exists(dest_dir):
        console.error(f'Folder {dest_dir} not found.\n'
                      'Make sure you have set the module in the manifest or you are '
                      'using the CLI at project root directory.')
        sys.exit(1)
    dest = paths.join(dest_dir, dest_file)
    if paths.exists(dest):
        console.error(f'File {dest} already exist.')
        sys.exit(1)
    rendered = files.render_template(source_dir, source_template, params)
    files.write(dest, rendered)


def _update_init(path: str, module: str, folder: str, name: str, class_name: str):
    file_path = paths.join(path, '__init__.py')
    files.write(file_path, f'from {module}.{folder}.{name} import {class_name}\n', mode='a+')


def _create_model(context: 'blnt.BolinetteContext', console: Console, name: str):
    module = context.manifest['module']
    dest_dir = context.root_path(module, 'models')
    class_name = name[0].upper() + name[1:]
    _create_file(console,
                 source_dir=context.internal_files_path('cli', 'templates'),
                 source_template='model.py.jinja2',
                 dest_dir=dest_dir,
                 dest_file=f'{name}.py',
                 params={'name': name, 'class': class_name})
    _update_init(dest_dir, module, 'models', name, class_name)


def _create_service(context: 'blnt.BolinetteContext', console: Console, name: str):
    module = context.manifest['module']
    dest_dir = context.root_path(module, 'services')
    class_name = name[0].upper() + name[1:]
    _create_file(console,
                 source_dir=context.internal_files_path('cli', 'templates'),
                 source_template='service.py.jinja2',
                 dest_dir=dest_dir,
                 dest_file=f'{name}.py',
                 params={'name': name, 'class': class_name})
    _update_init(dest_dir, module, 'services', name, f'{class_name}Service')


def _create_controller(context: 'blnt.BolinetteContext', console: Console, name: str):
    module = context.manifest['module']
    dest_dir = context.root_path(module, 'controllers')
    class_name = name[0].upper() + name[1:]
    _create_file(console,
                 source_dir=context.internal_files_path('cli', 'templates'),
                 source_template='controller.py.jinja2',
                 dest_dir=dest_dir,
                 dest_file=f'{name}.py',
                 params={'name': name, 'class': class_name, 'module': module})
    _update_init(dest_dir, module, 'controllers', name, f'{class_name}Controller')


def _create_middleware(context: 'blnt.BolinetteContext', console: Console, name: str):
    module = context.manifest['module']
    dest_dir = context.root_path(module, 'middlewares')
    class_name = name[0].upper() + name[1:]
    _create_file(console,
                 source_dir=context.internal_files_path('cli', 'templates'),
                 source_template='middleware.py.jinja2',
                 dest_dir=dest_dir,
                 dest_file=f'{name}.py',
                 params={'name': name, 'class': class_name})
    _update_init(dest_dir, module, 'middlewares', name, f'{class_name}Middleware')


def _create_mixin(context: 'blnt.BolinetteContext', console: Console, name: str):
    module = context.manifest['module']
    dest_dir = context.root_path(module, 'mixins')
    class_name = name[0].upper() + name[1:]
    _create_file(console,
                 source_dir=context.internal_files_path('cli', 'templates'),
                 source_template='mixin.py.jinja2',
                 dest_dir=dest_dir,
                 dest_file=f'{name}.py',
                 params={'name': name, 'class': class_name})
    _update_init(dest_dir, module, 'mixins', name, f'{class_name}')


@command('new model', 'Create a new model file')
@command.argument('argument', 'name', summary='The new model\'s name')
@command.argument('flag', 'service', flag='s', summary='Create an associated service')
@command.argument('flag', 'controller', flag='c', summary='Create an associated controller')
async def create_model(context: 'blnt.BolinetteContext', name: str, service: bool, controller: bool):
    console = Console()
    _create_model(context, console, name)
    if service:
        _create_service(context, console, name)
    if controller:
        _create_controller(context, console, name)


@command('new service', 'Create a new service file')
@command.argument('argument', 'name', summary='The new service\'s name')
@command.argument('flag', 'controller', flag='c', summary='Create an associated controller')
async def create_service(context: 'blnt.BolinetteContext', name: str, controller: bool):
    console = Console()
    _create_service(context, console, name)
    if controller:
        _create_controller(context, console, name)


@command('new controller', 'Create a new controller file')
@command.argument('argument', 'name', summary='The new controller\'s name')
async def create_controller(context: 'blnt.BolinetteContext', name: str):
    console = Console()
    _create_controller(context, console, name)


@command('new middleware', 'Create a new middleware file')
@command.argument('argument', 'name', summary='The new middleware\'s name')
async def create_middleware(context: 'blnt.BolinetteContext', name: str):
    console = Console()
    _create_middleware(context, console, name)


@command('new mixin', 'Create a new mixin file')
@command.argument('argument', 'name', summary='The new mixin\'s name')
async def create_mixin(context: 'blnt.BolinetteContext', name: str):
    console = Console()
    _create_mixin(context, console, name)
