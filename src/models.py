from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import UUID

from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geography, Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Mapped

# create the extension
db = SQLAlchemy()


roles_to_users = db.Table(
    "role_to_user",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column(
        "user_id", UUID(as_uuid=False), db.ForeignKey("user.id"), primary_key=True
    ),
)


class User(db.Model):
    id = db.Column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    access_tokens = db.relationship("AccessToken", backref="user", lazy=True)
    refresh_tokens = db.relationship("RefreshToken", backref="user", lazy=True)


class AccessToken(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("user.id"), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    user_agent = db.Column(db.String(50), nullable=False)
    token = db.Column(db.String(1000), nullable=False, unique=True)
    expiration = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False)


class RefreshToken(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("user.id"), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    user_agent = db.Column(db.String(50), nullable=False)
    token = db.Column(db.String(1000), nullable=False, unique=True)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    expiration = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_used_at = db.Column(db.DateTime(timezone=True))


roles_to_permissions = db.Table(
    "role_to_permission",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column(
        "permission_id", db.Integer, db.ForeignKey("permission.id"), primary_key=True
    ),
)


class Role(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    permissions: Mapped[list[Permission]] = db.relationship(
        secondary=roles_to_permissions,
        backref="roles",
        lazy=True,
    )
    users: Mapped[list[User]] = db.relationship(
        secondary=roles_to_users,
        backref="roles",
        lazy=True,
    )


class Permission(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)


class LemonadeStand(db.Model):
    __tablename__ = "lemonade_stand"
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    location = db.Column(Geometry("POINT"), nullable=False)
    owner_id = db.Column(UUID(as_uuid=False), db.ForeignKey("user.id"), nullable=False)
    owner = db.relationship("User", backref="lemonade_stands", lazy=True)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    current_price_in_micros = db.Column(
        db.Integer, nullable=False
    )  # normal price * 1,000
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)

    def get_location(self) -> tuple[float, float]:
        coords = to_shape(self.location).coords
        return (coords[0][0], coords[0][1])


class LemonadeStandSale(db.Model):
    __tablename__ = "lemonade_stand_sale"
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    lemonade_stand_id = db.Column(
        db.Integer, db.ForeignKey("lemonade_stand.id"), nullable=False
    )
    lemonade_stand = db.relationship(
        "LemonadeStand", backref="sales", lazy=True, uselist=False
    )
    date = db.Column(db.DateTime(timezone=True), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    price_in_micros = db.Column(db.Integer, nullable=False)  # normal price * 1,000
