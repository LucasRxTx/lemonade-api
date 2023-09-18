import datetime
import logging

import flask
import sqlalchemy
from sqlalchemy.sql import func

import services.auth
import services.stand
from exceptions import NotFound, StandAlreadyExistsError, UnprocessableEntityError
from models import LemonadeStand, LemonadeStandSale, db
from serialization import (
    CreateStandRequest,
    LemonadeSaleResponse,
    SellLemonadeRequest,
    StandResponse,
)

logger = logging.getLogger(__name__)
stands_blueprint = flask.Blueprint("stands", __name__)


def stand_orm_to_response(stand_orm: LemonadeStand) -> StandResponse:
    return StandResponse(
        id=stand_orm.id,
        owner_id=stand_orm.owner_id,
        name=stand_orm.name,
        location=stand_orm.get_location(),
        created_at=stand_orm.created_at,
        updated_at=stand_orm.updated_at,
        current_price_in_micros=stand_orm.current_price_in_micros,
        currency=stand_orm.currency,
        sales=stand_orm.sales,
    )


@stands_blueprint.route("/my/stands", methods=["GET"])
@services.auth.auth_required(permissions=["lemonade-stand.my.stands.get"])
def get_my_stands():
    stands = services.stand.get_owners_lemonade_stands(owner_id=flask.g.user.id)
    return flask.jsonify(
        stand_orm_to_response(stand).model_dump(by_alias=True) for stand in stands
    )


@stands_blueprint.route("/my/stands/<int:stand_id>", methods=["GET"])
@services.auth.auth_required(permissions=["lemonade-stand.my.stands.get"])
def get_my_stand(stand_id: int):
    stand = services.stand.get_owners_lemonade_stand_by_id(
        owner_id=flask.g.user.id,
        stand_id=stand_id,
    )
    if stand is None:
        raise NotFound()

    r = stand_orm_to_response(stand).model_dump(by_alias=True)

    return flask.jsonify(r)


@stands_blueprint.route("/my/stands/<int:stand_id>/sales", methods=["POST"])
@services.auth.auth_required(
    permissions=["lemonade-stand.my.stands.sales.create"]
)
def sell_lemonade(stand_id: int):
    stand = services.stand.get_owners_lemonade_stand_by_id(
        owner_id=flask.g.user.id, stand_id=stand_id
    )
    if stand is None:
        raise NotFound()

    data = flask.request.get_json()
    match data:
        case dict():
            try:
                sell_lemonade_request = SellLemonadeRequest(**data)
            except TypeError():
                raise UnprocessableEntityError()
        case _:
            raise UnprocessableEntityError()

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    sale = LemonadeStandSale(
        lemonade_stand=stand,
        currency=stand.currency,
        price_in_micros=sell_lemonade_request.price_in_micros,
        date=now,
    )

    db.session.add(sale)

    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        flask.abort(400)

    return "", 201


@stands_blueprint.route("/my/stands/<int:stand_id>/sales", methods=["GET"])
@services.auth.auth_required(permissions=["lemonade-stand.my.stands.sales.get"])
def get_my_stand_sales(stand_id: int):
    stand = services.stand.get_owners_lemonade_stand_by_id(
        owner_id=flask.g.user.id,
        stand_id=stand_id,
    )
    if stand is None:
        raise NotFound()

    return flask.jsonify(
        LemonadeSaleResponse.from_orm(sale).model_dump(by_alias=True)
        for sale in stand.sales
    )


@stands_blueprint.route("/my/sales", methods=["GET"])
@services.auth.auth_required(permissions=["lemonade-stand.my.stands.sales.get"])
def get_my_sales():
    stands = services.stand.get_owners_lemonade_stands(owner_id=flask.g.user.id)
    stand_ids = [stand.id for stand in stands]

    sales = services.stand.get_lemonade_stand_sales_by_ids(stand_ids)

    return flask.jsonify(
        LemonadeSaleResponse.from_orm(sale).model_dump(by_alias=True) for sale in sales
    )


@stands_blueprint.route("/my/stands", methods=["POST"])
@services.auth.auth_required(permissions=["lemonade-stand.my.stands.create"])
def create_my_stand():
    data = flask.request.get_json()
    match data:
        case dict():
            try:
                create_stand_request = CreateStandRequest(**data)
            except TypeError:
                raise UnprocessableEntityError()
        case _:
            raise UnprocessableEntityError()

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    stand = LemonadeStand(
        created_at=now,
        updated_at=now,
        location=f"POINT({create_stand_request.location[0]:.6f} {create_stand_request.location[1]:.6f})",
        owner_id=flask.g.user.id,
        name=create_stand_request.name,
        currency=create_stand_request.currency,
        current_price_in_micros=create_stand_request.current_price_in_micros,
    )
    db.session.add(stand)
    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        raise StandAlreadyExistsError()

    return (
        "",
        201,
        {"Location": flask.url_for("stands.get_my_stand", stand_id=stand.id)},
    )


@stands_blueprint.route("/stands/near-me", methods=["GET"])
def get_stands_near_me():
    try:
        longitude = flask.request.args.get("longitude")
        latitude = flask.request.args.get("latitude")
        if not longitude and not latitude:
            raise UnprocessableEntityError()

        longitude = float(longitude)
        latitude = float(latitude)

        stands = (
            db.session.query(
                LemonadeStand.name,
                LemonadeStand.current_price_in_micros,
                func.ST_DistanceSphere(
                    LemonadeStand.location,
                    func.ST_GeomFromText(f"POINT({longitude} {latitude})"),
                ).label("distance"),
            )
            .filter(
                func.ST_DWithin(
                    LemonadeStand.location,
                    func.ST_GeomFromText(f"POINT({longitude} {latitude})"),
                    50000,  # 50km
                )
            )
            .limit(5)
            .all()
        )
    except Exception as e:
        logger.exception("Failed to get stands near me")
        raise Exception("Failed to get stands near me") from e

    return flask.jsonify(
        dict(
            name=stand.name,
            currentPriceInMicros=stand.current_price_in_micros,
            distance=stand.distance,
        )
        for stand in stands
    )
