from __future__ import annotations

import datetime
import random
import time

import flask
import sqlalchemy

import services.auth
import services.user
from exceptions import InvalidCredentialsError, UnprocessableEntityError
from models import db
from serialization import LoginRequest, RefreshTokenRequest

auth_blueprint = flask.Blueprint("auth", __name__)


@auth_blueprint.route("/auth/login", methods=["POST"])
def login():
    match flask.request.get_json():
        case dict() as data:
            try:
                login_request = LoginRequest(**data)
            except TypeError:
                raise UnprocessableEntityError()
        case _:
            raise UnprocessableEntityError()

    user = services.user.get_user_by_email(email=login_request.email.lower())

    if user is None:
        # Simulate a slow response to prevent timing attacks
        time.sleep(random.uniform(0.1, 0.3))
        raise InvalidCredentialsError()

    if services.auth.check_password_hash(
        password_hash=user.password_hash,
        password_plain_text=login_request.password,
    ):
        token_pair = services.auth.create_token_pair_for_user(user)
        db.session.commit()

        return flask.jsonify(token_pair.model_dump(by_alias=True)), 201
    else:
        raise InvalidCredentialsError()


@auth_blueprint.route("/auth/revoke", methods=["POST"])
@services.auth.auth_required(permissions=[])
def revoke():
    # Invalidate token
    match flask.request.get_json():
        case dict() as data:
            try:
                refresh_token_request = RefreshTokenRequest(**data)
            except TypeError:
                raise UnprocessableEntityError()
        case _:
            raise UnprocessableEntityError()

    services.auth.invalidate_refresh_token(token=refresh_token_request.refresh_token)
    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        flask.abort(400)

    return "", 201


@auth_blueprint.route("/auth/refresh", methods=["POST"])
def refresh_token():
    # check refesh token is valid
    match flask.request.get_json():
        case dict() as data:
            try:
                refresh_token_request = RefreshTokenRequest(**data)
            except TypeError:
                raise UnprocessableEntityError()
        case _:
            raise UnprocessableEntityError()

    refresh_claims = services.auth.decode_jwt_refresh_token(
        refresh_token_request.refresh_token
    )
    existing_refresh_token = services.auth.get_existing_refresh_token_for_user(
        user_id=refresh_claims.sub,
        refresh_token=refresh_token_request.refresh_token,
    )

    if existing_refresh_token is None:
        raise InvalidCredentialsError()

    existing_refresh_token.last_used_at = datetime.datetime.now(
        tz=datetime.timezone.utc
    )
    existing_refresh_token.revoked = True

    user = services.user.get_user_by_id(id=existing_refresh_token.user_id)
    if user is None:
        raise InvalidCredentialsError()

    token_pair = services.auth.create_token_pair_for_user(user)

    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        flask.abort(400)

    return flask.jsonify(token_pair.model_dump(by_alias=True)), 201
