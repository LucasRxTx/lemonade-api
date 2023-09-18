from __future__ import annotations

import datetime

import pydantic


def to_camel(string: str) -> str:
    parts = string.split("_")
    if not parts:
        return string

    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class JsonBase(pydantic.BaseModel):
    class Config:
        from_attributes = True
        alias_generator = to_camel
        populate_by_name = True
        arbitrary_types_allowed = True


class CreateUserRequest(JsonBase):
    email: str
    password: pydantic.SecretStr
    first_name: str
    last_name: str
    age: int


class LoginRequest(JsonBase):
    email: str
    password: pydantic.SecretStr


class GetUserResponse(JsonBase):
    id: str
    email: str
    first_name: str
    last_name: str
    age: int


class RevokeTokenRequest(JsonBase):
    refresh_token: str


class JWTRefreshTokenClaims(pydantic.BaseModel):
    sub: str
    aud: str
    iss: str
    exp: int
    iat: int
    jwtid: str


class JWTAccessTokenClaims(JWTRefreshTokenClaims):
    roles: list[str]


class TokenPair(JsonBase):
    access_token: str
    refresh_token: str


class RefreshTokenRequest(JsonBase):
    refresh_token: str


class RefreshTokenResponse(JsonBase):
    access_token: str
    refresh_token: str


class AccessTokenResponse(JsonBase):
    id: int
    user_id: str
    ip_address: str
    user_agent: str
    token: str
    expiration: datetime.datetime
    created_at: datetime.datetime
    last_seen_at: datetime.datetime


class SalesRelationship(JsonBase):
    date: datetime.datetime
    currency: str
    price_in_micros: int


class StandResponse(JsonBase):
    id: int
    name: str
    owner_id: str
    location: tuple[float, float]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    currency: str
    current_price_in_micros: int
    sales: list[SalesRelationship]


StandResponse.model_rebuild()


class CreateStandRequest(JsonBase):
    name: str
    location: tuple[float, float]
    currency: str
    current_price_in_micros: int


class RoleRelationship(JsonBase):
    id: int
    name: str


class PermissionResponse(JsonBase):
    id: int
    name: str
    roles: list[RoleRelationship]


PermissionResponse.model_rebuild()


class PermissionRelationship(JsonBase):
    id: int
    name: str


class RoleResponse(JsonBase):
    id: int
    name: str
    permissions: list[PermissionRelationship]


RoleResponse.model_rebuild()


class SellLemonadeRequest(JsonBase):
    price_in_micros: int


class LemonadeSaleResponse(JsonBase):
    date: datetime.datetime
    currency: str
    price_in_micros: int
