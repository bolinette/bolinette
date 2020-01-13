import os

import jinja2

from bolinette.templating import paths


def get_default_path():
    return paths.join(paths.dirname(__file__), 'files')


def render(path, params, base_path=None):
    if base_path is None:
        base_path = get_default_path()
    complete_path = paths.join(base_path, path)
    template_path, template_name = paths.split(complete_path)
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=template_path),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = jinja_env.get_template(template_name)
    return template.render(**params)


def render_directory(origin, dest, params):
    if not os.path.exists(dest):
        paths.mkdir(dest)
    for f in os.listdir(origin):
        if os.path.isdir(join(origin, f)):
            render_directory(join(origin, f), join(dest, f), params)
        if os.path.isfile(join(origin, f)):
            paths.copy(join(origin, f), join(dest, f), params)
