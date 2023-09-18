import datetime
from typing import Optional

import werkzeug.security

from exceptions import ServerError
from models import Role, User, db
import pydantic


def get_user_by_id(id: int) -> Optional[User]:
    return db.session.get(User, id)


def get_user_by_email(email: str) -> Optional[User]:
    return User.query.filter_by(email=email).one_or_none()


def get_all_users() -> list[User]:
    return User.query.all()


def create_user(
    email: str,
    first_name: str,
    last_name: str,
    age: int,
    password: pydantic.SecretStr,
) -> None:
    password_hash = werkzeug.security.generate_password_hash(
        password.get_secret_value()
    )

    role = Role.query.filter_by(name="lemonade-stand.user").one_or_none()
    if role is None:
        raise ServerError()

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.add(
        User(
            email=email.lower(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            age=age,
            roles=[role],
            created_at=now,
            updated_at=now,
        )
    )


def get_permissions_for_user(user: User) -> list[str]:
    permissions = []
    for role in user.roles:
        for permission in role.permissions:
            permissions.append(permission.name)

    return permissions
