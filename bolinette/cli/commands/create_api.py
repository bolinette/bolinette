import os
import virtualenv
import subprocess

from cli import env
from cli.parser.utils import join, mkdir, random_string, copy


def create_api(**kwargs):
    cwd = env['cwd']
    module = kwargs.get('module')
    path = join(cwd, module)
    origin = join(env['origin'], 'files')
    if os.path.isdir(path):
        return print(f'"{path}" folder already exists.')
    try:
        print('* Creating folder')
        mkdir(path)

        print('* Creating virtual environment')
        virtualenv.create_environment(join(path, 'venv'))

        mkdir(join(path, 'instance'))
        mkdir(join(path, module))
        kwargs['path'] = path
        kwargs['module'] = module
        kwargs['secret_key'] = random_string(32)
        kwargs['jwt_secret_key'] = random_string(32)

        print('* Creating files')
        copy(join(origin, 'env.jinja2'), join(path, 'instance', '.env'), kwargs)
        copy(join(origin, 'requirements.jinja2'), join(path, 'requirements.txt'), kwargs)
        copy(join(origin, 'install.jinja2'), join(path, 'install.sh'), kwargs)
        copy(join(origin, 'app.jinja2'), join(path, module, 'app.py'), kwargs)
        copy(join(origin, 'server.jinja2'), join(path, 'server.py'), kwargs)
        copy(join(origin, 'module_init.jinja2'), join(path, module, '__init__.py'), kwargs)
        copy(join(origin, 'manifest.jinja2'), join(path, 'manifest.bolinette.yaml'), kwargs)

        print('* Installing pip packages')
        process = subprocess.Popen(['/bin/bash', join(path, 'install.sh')], stdout=subprocess.PIPE)
        for line in iter(process.stdout.readline, ''):
            if len(line) > 0:
                print(line.rstrip().decode('utf-8'))
            else:
                break

        print(f'* Bolinette app "{module}" successfully created')
    except OSError:
        return print(f'Unable to create files, check your privileges.')
