import sys
import importlib

from bolinette import Bolinette, Console
from bolinette.utils import paths, files


def _find_module(path: str):
    manifest = files.read_manifest(path) or {}
    return manifest.get('module', None)


def _get_blnt_instance(console: Console, path: str):
    module_name = _find_module(path)
    if module_name is not None and paths.exists(paths.join(path, module_name)):
        if path not in sys.path:
            sys.path.append(path)
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
    _blnt = _get_blnt_instance(Console(), paths.cwd())
    _blnt.exec_cmd_args()


if __name__ == '__main__':
    main()
