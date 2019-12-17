import example.controllers
from example.app import bolinette


# Picked up by gunicorn to launch production server
application = bolinette.app
