import logging

import flask
import pydantic
from werkzeug.exceptions import NotFound

from exceptions import (
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidPermissionsError,
    ServerError,
    StandAlreadyExistsError,
    UnprocessableEntityError,
    UserAlreadyExistsError,
)
from models import db

logger = logging.getLogger(__name__)


def handle_error(error):
    try:
        db.session.rollback()
    except Exception:
        logger.exception("Failed to rollback session.")

    match error:
        case pydantic.ValidationError() as e:
            return flask.jsonify({"error": e.errors()}), 400
        case UserAlreadyExistsError():
            return flask.jsonify({"error": "User already exists."}), 409
        case StandAlreadyExistsError():
            return flask.jsonify({"error": "Stand already exists."}), 409
        case InvalidCredentialsError():
            return flask.jsonify({"error": "Invalid username or password."}), 401
        case ServerError():
            return flask.jsonify({"error": "Internal server error."}), 500
        case ExpiredTokenError():
            return flask.jsonify({"error": "Token has expired."}), 401
        case InvalidPermissionsError():
            return flask.jsonify({"error": "Invalid permissions."}), 403
        case NotFound():
            return flask.jsonify({"error": "Not found."}), 404
        case UnprocessableEntityError():
            return (
                flask.jsonify(
                    {"error": "Something essensial is missing from your request."}
                ),
                422,
            )
        case _:
            return flask.jsonify({"error": "Internal server error."}), 500
