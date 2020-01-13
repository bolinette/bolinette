import os

import jinja2


def get_default_path():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'files')


def render(path, params, base_path=None):
    if base_path is None:
        base_path = get_default_path()
    complete_path = os.path.join(base_path, path)
    template_path, template_name = os.path.split(complete_path)
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=template_path),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = jinja_env.get_template(template_name)
    return template.render(**params)
