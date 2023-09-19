import datetime
import functools
import logging
import time
import uuid
from typing import Optional, NewType, Any

import flask
import jwt
import werkzeug.security

import constants
from exceptions import (
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidPermissionsError,
)
from models import AccessToken, RefreshToken, User, db
from serialization import (
    TokenPair,
    JWTAccessTokenClaims,
    JWTRefreshTokenClaims,
)
import services.user
from custom_types import PasswordPlainText, PasswordHashed


logger = logging.getLogger(__name__)


RawAccessToken = NewType("RawAccessToken", str)


def seconds_since_epoch():
    """Return the number of seconds since the epoch.

    Throws away any fractional seconds.
    """
    return int(time.time())


def get_raw_access_token_from_request_headers() -> RawAccessToken:
    """Get a ``RawAccessToken`` from flask request headers.

    Raises:
        InvalidCredentialsError: If raw token is not found.
    """
    # Validate token and claims
    token = flask.request.headers.get("Authorization")
    if token is None:
        raise InvalidCredentialsError()

    if token.startswith(constants.TOKEN_SCHEME):
        # Remove token scheme prefix if it was given.
        # Example:  "Bearer eyJhbGciOiJIUzI1...""
        # should be: "eyJhbGciOiJIUzI1..."
        token = token[len(constants.TOKEN_SCHEME) + 1 :]

    return RawAccessToken(token)


def __decode_token_claims(token: str) -> Any:
    try:
        return jwt.decode(
            jwt=token,
            key=flask.current_app.config["SECRET_KEY"],
            algorithms=[flask.current_app.config["JWT_ALGORITHM"]],
            audience=flask.current_app.config["JWT_AUDIENCE"],
        )
    except jwt.exceptions.ExpiredSignatureError:
        raise ExpiredTokenError()
    except jwt.exceptions.DecodeError:
        raise InvalidCredentialsError()
    except jwt.InvalidTokenError:
        raise InvalidCredentialsError()


def decode_jwt_access_token(access_token: str) -> JWTAccessTokenClaims:
    """Decode a JWT token."""
    claims = __decode_token_claims(access_token)

    token_claims: Optional[JWTAccessTokenClaims] = None
    match claims:
        case dict():
            try:
                token_claims = JWTAccessTokenClaims(**claims)
            except TypeError:
                raise InvalidCredentialsError()
        case _:
            raise InvalidCredentialsError()

    return token_claims


def decode_jwt_refresh_token(refresh_token: str) -> JWTRefreshTokenClaims:
    """Decode a JWT token."""
    claims = __decode_token_claims(refresh_token)

    token_claims: Optional[JWTRefreshTokenClaims] = None
    match claims:
        case dict():
            try:
                token_claims = JWTRefreshTokenClaims(**claims)
            except TypeError:
                raise InvalidCredentialsError()
        case _:
            raise InvalidCredentialsError()

    return token_claims


def get_access_token_by_raw_token(
    user_id: str,
    raw_access_token: RawAccessToken,
) -> Optional[AccessToken]:
    """Get and ``AccessToken`` using a raw token string.

    Parameters:
        user_id: User id of the token owner.
        raw_access_token: The encoded token as a string with no auth scheme prefix.
    """
    return AccessToken.query.filter_by(
        user_id=user_id,
        token=raw_access_token,
    ).one_or_none()


def validate_jwt_access_token(
    raw_access_token: RawAccessToken,
    token_claims: JWTAccessTokenClaims,
    permissions: list[str],
) -> None:
    """Validate access token is valid.

    If no exception is raised, then the access token is valid.

    Raises:
        InvalidCredentialsError: If access token is no longer valid
        InvalidPermissionsError: If the access token is valid, but does not have the required permissions.
    """
    # validate access_token
    access_token = get_access_token_by_raw_token(
        user_id=token_claims.sub,
        raw_access_token=raw_access_token,
    )
    if access_token is None:
        raise InvalidCredentialsError()

    # validate expiration
    if token_claims.exp < seconds_since_epoch():
        raise InvalidCredentialsError()

    access_token.last_seen_at = datetime.datetime.now(tz=datetime.timezone.utc)

    # validate permissions
    if not set(permissions).issubset(set(token_claims.roles)):
        raise InvalidPermissionsError()


def revoke_refresh_token(refresh_token: RefreshToken) -> None:
    """Revoke a users refresh token.

    Parameters:
        refresh_token:  The ``RefreshToken`` model.
    """
    refresh_token.last_used_at = datetime.datetime.now(tz=datetime.timezone.utc)
    refresh_token.revoked = True


def auth_required(permissions: list[str]):
    """Protect a route that requires auth.

    Tokens are expected to be given in the Authorization header.

    The token scheme prefix is stripped if provided.

    For example, if a Authorization header has a value of "Bearer eyJhbGciOiJIUzI1...",
    ``Bearer`` and the proceding whitespace will be stripped out to become
    "eyJhbGciOiJIUzI1...".

    Parameters:
        permissions: List of permissions required to access the given endpoint.

    Example Usage::

        @app.route("/protected", methods=["GET"])
        @services.auth.auth_required(permissions=["myapp.admin"])
        def get_all_users():
            ...

    """

    def inner_decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            # Validate token and claims
            token = get_raw_access_token_from_request_headers()
            token_claims = decode_jwt_access_token(token)

            # validate user exists
            user = services.user.get_user_by_id(token_claims.sub)
            if user is None:
                raise InvalidCredentialsError()

            validate_jwt_access_token(
                raw_access_token=token,
                token_claims=token_claims,
                permissions=permissions,
            )

            flask.g.user = user
            flask.g.token_claims = token_claims

            return f(*args, **kwargs)

        return decorated

    return inner_decorator


def create_access_token_for_user(
    user_id: str,
    permissions: list[str],
) -> str:
    """Create and access token for a user.

    Parameters:
        user_id: Id of the user.
        permissions:  Permissions for the user.
    """
    issued_at_seconds = seconds_since_epoch()

    return jwt.encode(
        payload=dict(
            sub=user_id,
            iss=flask.current_app.config["JWT_ISSUER"],
            aud=flask.current_app.config["JWT_AUDIENCE"],
            exp=issued_at_seconds + constants.MAX_AGE_OF_ACCESS_TOKEN,
            iat=issued_at_seconds,
            jwtid=str(uuid.uuid4()),
            roles=permissions,
        ),
        key=str(flask.current_app.config["SECRET_KEY"]),
        algorithm=flask.current_app.config["JWT_ALGORITHM"],
    )


def create_refresh_token_for_user(user_id) -> str:
    """Create a refresh token for a user.

    Parameters:
        user_id: The id of the user.
    """
    issued_at_seconds = seconds_since_epoch()

    return jwt.encode(
        payload=dict(
            sub=user_id,
            iss=flask.current_app.config["JWT_ISSUER"],
            aud=flask.current_app.config["JWT_AUDIENCE"],
            exp=issued_at_seconds + constants.MAX_AGE_OF_REFRESH_TOKEN,
            iat=issued_at_seconds,
            jwtid=str(uuid.uuid4()),
        ),
        key=str(flask.current_app.config["SECRET_KEY"]),
        algorithm=flask.current_app.config["JWT_ALGORITHM"],
    )


def register_token_pair_creation_for_user(
    user: User,
    ip_address: str,
    user_agent: str,
    token_pair: TokenPair,
) -> None:
    """Adds a token pair in the database.

    Parameters:
        user: User model
        ip_address: String version of the users ip address.
        user_agent: The user agent string for the user.
        token_pair:  The user's access / refresh token pair.
    """
    current_datetime_in_utc = datetime.datetime.now(tz=datetime.timezone.utc)

    db.session.add_all(
        [
            AccessToken(
                user_id=user.id,
                token=token_pair.access_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expiration=(
                    current_datetime_in_utc
                    + datetime.timedelta(seconds=constants.MAX_AGE_OF_ACCESS_TOKEN)
                ),
                created_at=current_datetime_in_utc,
                last_seen_at=current_datetime_in_utc,
            ),
            RefreshToken(
                user_id=user.id,
                token=token_pair.refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expiration=(
                    current_datetime_in_utc
                    + datetime.timedelta(constants.MAX_AGE_OF_REFRESH_TOKEN)
                ),
                created_at=current_datetime_in_utc,
            ),
        ]
    )


def create_token_pair_for_user(user: User) -> TokenPair:
    """Create a token pair for the user.

    Parameters:
        user: The user model.
    """
    # User did not have an active session, create one
    token_pair = TokenPair(
        access_token=create_access_token_for_user(
            user_id=user.id,
            permissions=services.user.get_permissions_for_user(user),
        ),
        refresh_token=create_refresh_token_for_user(user_id=user.id),
    )

    register_token_pair_creation_for_user(
        user=user,
        ip_address=flask.request.remote_addr or "",
        user_agent=flask.request.headers.get("User-Agent") or "",
        token_pair=token_pair,
    )

    return token_pair


def check_password_hash(
    password_hash: PasswordHashed,
    password_plain_text: PasswordPlainText,
) -> bool:
    """Check the password hash matches the provided plain text password."""
    return werkzeug.security.check_password_hash(
        password_hash,
        password_plain_text.get_secret_value(),
    )


def get_existing_refresh_token_for_user(
    user_id: str,
    refresh_token: str,
) -> Optional[RefreshToken]:
    """Get the users existing refresh token.

    Parameters:
        user_id: The user's id.
        refresh_token: The refresh token of the user.
    """
    return RefreshToken.query.filter_by(
        user_id=user_id,
        token=refresh_token,
        last_used_at=None,
        revoked=False,
    ).one_or_none()


def get_all_access_tokens_for_user(user_id: str) -> list[AccessToken]:
    """Get all of the users access tokens.

    Parameters:
        user_id: The user's id.
    """
    return AccessToken.query.filter_by(user_id=user_id).all()
