from flask import send_from_directory

from bolinette import env


def index():
    return send_from_directory(env['WEBAPP_FOLDER'], 'index.html')


def init_routes(app):
    app.add_url_rule('/', 'index', view_func=index)
