from flask_jwt_extended import get_jwt_identity

from bolinette.exceptions import APIError
from bolinette.services import user_service


def current_user():
    try:
        return user_service.get_by_username(get_jwt_identity())
    except APIError:
        return None
