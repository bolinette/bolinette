import jinja2
import yaml

from bolinette.utils import paths


def write(path, content, mode='w+'):
    with open(path, mode=mode) as file:
        file.write(content)


def append(path, content):
    write(path, content, mode='a+')


def read_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def read_version(path):
    try:
        with open(paths.join(path, '.version')) as f:
            for line in f:
                return line.strip().replace('\n', '')
    except FileNotFoundError:
        return None


def read_requirements(path):
    try:
        with open(paths.join(path, 'requirements.txt')) as f:
            return list(filter(lambda r: len(r), f.read().split('\n')))
    except FileNotFoundError:
        return []


def read_manifest(path):
    try:
        with open(paths.join(path, 'manifest.blnt.yml')) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def render_template(path, params):
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
