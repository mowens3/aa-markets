# flake8: noqa
"""Interactions with moonmining module"""

from collections import defaultdict
from typing import Dict, List

from moonmining.models.moons import Moon as MoonMiningMoon

from eveuniverse.models import EveType

from metenox.app_settings import (
    METENOX_HARVEST_REPROCESS_YIELD,
    METENOX_HOURLY_HARVEST_VOLUME,
)
from metenox.models import Moon as MetenoxMoon

EVE_MOON_MATERIALS_GROUP_ID = 427  # group id of all moon goo


def list_all_moons() -> List[MetenoxMoon]:
    """Returns all known moons"""
    return MetenoxMoon.objects.all()


def get_metenox_hourly_harvest(moon_id: int) -> Dict[EveType, int]:
    """
    Will return how much moon materials a Metenox anchored on the given moon will harvest from the moon ID
    The output dict is {moon_goo_type: moon_goo_amount_per_hour}
    """
    try:
        moon = MoonMiningMoon.objects.get(eve_moon_id=moon_id)
    except MoonMiningMoon.DoesNotExist:
        return {}

    hourly_ore_amounts = {
        moon_product.ore_type: moon_product.amount * METENOX_HOURLY_HARVEST_VOLUME
        for moon_product in moon.products_sorted()
    }

    outputs = defaultdict(int)

    rock_volume = 10
    rock_to_reprocess = 100

    # https://gitlab.com/ErikKalkoken/aa-moonmining/-/blob/master/moonmining/models/extractions.py#L422
    for ore_type, ore_amount in hourly_ore_amounts.items():
        total_rocks = ore_amount / rock_volume
        number_reprocess = total_rocks / rock_to_reprocess

        # type_material is an EveTypeMaterial
        # https://django-eveuniverse.readthedocs.io/en/latest/api.html#eveuniverse.models.EveTypeMaterial
        for type_material in ore_type.materials.select_related(
            "material_eve_type__market_price"
        ):
            if (
                type_material.material_eve_type.eve_group.id
                == EVE_MOON_MATERIALS_GROUP_ID
            ):
                amount_material = int(
                    number_reprocess
                    * METENOX_HARVEST_REPROCESS_YIELD
                    * type_material.quantity
                )
                outputs[type_material.material_eve_type] += amount_material

    return outputs
