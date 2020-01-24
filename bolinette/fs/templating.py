import os
import re

import jinja2

from bolinette.fs import paths


def render(path, params):
    template_path, template_name = paths.split(path)
    if not len(template_path):
        template_path = paths.join(paths.dirname(__file__), 'files')
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=template_path),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = jinja_env.get_template(template_name)
    return template.render(**params)


def copy(origin, dest, params):
    content = render(origin, params)
    paths.write(re.sub(r'\.jinja2$', '', dest), content)


def render_directory(origin, dest, params):
    if not os.path.exists(dest):
        paths.mkdir(dest)
    for f in os.listdir(origin):
        if os.path.isdir(paths.join(origin, f)):
            render_directory(paths.join(origin, f), paths.join(dest, f), params)
        if os.path.isfile(paths.join(origin, f)):
            copy(paths.join(origin, f), paths.join(dest, f), params)
