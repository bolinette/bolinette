import importlib

from bolinette import blnt, Bolinette
from bolinette.utils import paths

context = blnt.BolinetteContext(paths.dirname(__file__))


def find_module():
    manifest = context.manifest
    return manifest.get('module', None)


def get_blnt_instance():
    module_name = find_module()
    if module_name is not None and paths.exists(context.root_path(module_name)):
        module = importlib.import_module(module_name)
        main_func = next(iter([f for f in module.__dict__.values()
                               if getattr(f, '__blnt__', None) == '__blnt_main__']), None)
        return main_func()
    return Bolinette()


def main():
    _blnt = get_blnt_instance()
    _blnt.exec_cmd_args()


if __name__ == '__main__':
    main()
