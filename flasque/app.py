from flask import Flask
from flask_script import Manager

from flasque import env

app = Flask(__name__)
manager = Manager(app)
env.init(app)
