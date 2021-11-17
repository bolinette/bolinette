import sys
import importlib

from bolinette import Bolinette, Console
from bolinette.utils import paths, files


def _find_module():
    manifest = files.read_manifest(paths.cwd()) or {}
    return manifest.get('module', None)


def _get_blnt_instance(console: Console):
    module_name = _find_module()
    if module_name is not None and paths.exists(paths.join(paths.cwd(), module_name)):
        module = importlib.import_module(module_name)
        main_func = next(iter([f for f in module.__dict__.values()
                               if callable(f) and getattr(f, '__blnt__', None) == '__blnt_main__']), None)
        if main_func is None:
            console.error(f'No main func found in {module_name} module. '
                          'Make sure to import a @main_func decorated function in the module\'s __init__.py file.')
            sys.exit(1)
        instance = main_func()
        if not isinstance(instance, Bolinette):
            console.error('The main_func did not return a Bolinette instance.')
            sys.exit(1)
        return instance
    return Bolinette(_anonymous=True)


def main():
    _blnt = _get_blnt_instance(Console())
    _blnt.exec_cmd_args()


if __name__ == '__main__':
    main()
