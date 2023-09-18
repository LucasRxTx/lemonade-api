from typing import Optional

from models import LemonadeStand, LemonadeStandSale


def get_owners_lemonade_stands(owner_id) -> list[LemonadeStand]:
    return LemonadeStand.query.filter_by(owner_id=owner_id).all()


def get_owners_lemonade_stand_by_id(owner_id, stand_id) -> Optional[LemonadeStand]:
    return LemonadeStand.query.filter_by(owner_id=owner_id, id=stand_id).one_or_none()


def get_lemonade_stand_sales_by_ids(
    lemonade_stand_sale_ids: list[str],
) -> list[LemonadeStandSale]:
    return LemonadeStandSale.query.filter(
        LemonadeStandSale.lemonade_stand_id.in_(lemonade_stand_sale_ids)
    ).all()
