from __future__ import annotations

import flask
import sqlalchemy

import services.auth
import services.user
from exceptions import UnprocessableEntityError, UserAlreadyExistsError
from models import db
from serialization import CreateUserRequest, GetUserResponse

users_blueprint = flask.Blueprint("users", __name__)


@users_blueprint.route("/users", methods=["GET"])
@services.auth.auth_required(permissions=["lemonade-stand.admin.users.get"])
def get_all_users():
    users = services.user.get_all_users()
    users_data = [GetUserResponse.model_validate(user) for user in users]
    return flask.jsonify(user.model_dump_json(by_alias=True) for user in users_data)


@users_blueprint.route("/users/<int:id>", methods=["GET"])
@services.auth.auth_required(permissions=["lemonade-stand.admin.users.get"])
def get_user(id: int):
    user = services.user.get_user_by_id(id) or flask.abort(404)

    user_data = GetUserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        age=user.age,
    )

    return flask.jsonify(user_data.model_dump(by_alias=True))


@users_blueprint.route("/users", methods=["POST"])
def create_user():
    match flask.request.get_json():
        case dict() as data:
            try:
                create_user_request = CreateUserRequest(**data)
            except TypeError:
                raise UnprocessableEntityError()
        case _:
            raise UnprocessableEntityError()

    services.user.create_user(
        email=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        age=create_user_request.age,
        password=create_user_request.password,
    )

    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        raise UserAlreadyExistsError()

    return "", 201


@users_blueprint.route("/users/me", methods=["GET"])
@services.auth.auth_required(permissions=["lemonade-stand.me.get"])
def get_me():
    return flask.jsonify(
        GetUserResponse.model_validate(flask.g.user).model_dump(by_alias=True)
    )
