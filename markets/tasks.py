"""Tasks."""

from typing import List, Optional

from celery import shared_task
from moonmining.constants import EveTypeId
from moonmining.models.moons import Moon as MoonminingMoon

from eveuniverse.constants import EveGroupId
from eveuniverse.models import EveSolarSystem

from allianceauth.analytics.tasks import analytics_event
from allianceauth.services.hooks import get_extension_logger

from markets.api.fuzzwork import BuySell, get_type_ids_prices
from markets.esi import (
    DownTimeError,
    get_corporation_markets_assets,
    get_markets_from_esi,
    get_structure_info_from_esi,
)
from markets.models import (
    EveTypePrice,
    HoldingCorporation,
    Markets,
    MarketsHourlyProducts,
    MarketsStoredMoonMaterials,
    MarketsTag,
    Moon,
)
from markets.moons import get_markets_hourly_harvest

logger = get_extension_logger(__name__)


class TaskError(Exception):
    """To be raised when a task fails"""


@shared_task
def update_all_holdings():
    """
    Update all active owners on the application
    """
    holding_corps = HoldingCorporation.objects.filter(is_active=True)
    logger.info("Starting update for %s owner(s)", {len(holding_corps)})
    for holding in holding_corps:
        update_holding.delay(holding.corporation.corporation_id)


@shared_task
def update_holding(holding_corp_id: int):
    """
    Updated the list of markets under a specific owner
    If harvest is set to True the harvest components are also recalculated
    """

    logger.info("Updating corporation id %s", holding_corp_id)

    holding_corp = HoldingCorporation.objects.get(
        corporation__corporation_id=holding_corp_id
    )

    if len(holding_corp.active_owners()) == 0:
        logger.info("No active owners for corporation id %s. Skipping", holding_corp_id)
        return

    try:
        markets_info = get_markets_from_esi(holding_corp)
    except DownTimeError:
        logger.warning("Currently at downtime. Exiting update")
        return

    markets_info_dic = {
        markets["structure_id"]: markets for markets in markets_info
    }

    markets_ids = set(markets["structure_id"] for markets in markets_info)

    try:
        markets_asset_dic = get_corporation_markets_assets(
            holding_corp, markets_ids
        )
    except DownTimeError:
        logger.warning("Currently at downtime. Exiting update")
        return

    current_markets_ids = set(
        markets.structure_id
        for markets in Markets.objects.filter(corporation=holding_corp)
    )

    disappeared_markets_ids = (
        current_markets_ids - markets_ids
    )  # markets that have been unanchored/destroyed/transferred
    Markets.objects.filter(structure_id__in=disappeared_markets_ids).delete()

    missing_markets_ids = markets_ids - current_markets_ids
    for markets_id in missing_markets_ids:
        location_info = get_structure_info_from_esi(holding_corp, markets_id)
        create_markets.delay(
            holding_corp.corporation.corporation_id,
            markets_info_dic[markets_id],
            location_info,
        )

    markets_to_updates = (
        current_markets_ids - disappeared_markets_ids - missing_markets_ids
    )
    for markets_id in markets_to_updates:
        update_markets.delay(
            markets_id, markets_info_dic[markets_id], markets_asset_dic[markets_id]
        )

    holding_corp.set_update_time_now()


@shared_task
def create_markets(
    holding_corporation_id: int, structure_info: dict, location_info: dict
):
    """
    Creates and adds the Markets in the database
    """
    holding_corporation = HoldingCorporation.objects.get(
        corporation__corporation_id=holding_corporation_id
    )
    logger.info(
        "Creating markets %s for %s",
        structure_info["structure_id"],
        holding_corporation,
    )
    solar_system, _ = EveSolarSystem.objects.get_or_create_esi(
        id=location_info["solar_system_id"]
    )
    try:
        nearest_celestial = solar_system.nearest_celestial(
            x=location_info["position"]["x"],
            y=location_info["position"]["y"],
            z=location_info["position"]["z"],
            group_id=EveGroupId.MOON,
        )
    except OSError as exc:
        logger.exception("%s: Failed to fetch nearest celestial", structure_info)
        raise exc

    if not nearest_celestial or nearest_celestial.eve_type.id != EveTypeId.MOON:
        logger.exception(
            "Couldn't find the moon corresponding to markets %s", structure_info
        )
        raise TaskError(
            f"Couldn't fetch the markets moon. Markets id {structure_info['structure_id']}."
            f"Structure position {location_info['position']}"
        )

    eve_moon = nearest_celestial.eve_object
    moon, _ = Moon.objects.get_or_create(eve_moon=eve_moon)

    markets = Markets(
        moon=moon,
        structure_name=structure_info["name"],
        structure_id=structure_info["structure_id"],
        corporation=holding_corporation,
    )
    markets.save()

    default_tags = MarketsTag.objects.filter(default=True)

    markets.tags.add(*default_tags)


@shared_task()
def update_markets(
    markets_structure_id: int,
    structure_info: dict,
    markets_assets: Optional[List[dict]] = None,
):
    """
    Updates a markets already existing in the database. Already receives the fetched ESI information of the structure
    """

    logger.info("Updating markets id %s", markets_structure_id)

    markets = Markets.objects.get(structure_id=markets_structure_id)

    if markets.structure_name != structure_info["name"]:
        logger.info("Updating markets id %s name", markets_structure_id)
        markets.structure_name = structure_info["name"]

    markets.fuel_blocks_count = 0
    fuel_blocks = 0
    stored_products_to_update = []
    for asset in markets_assets:
        if asset["location_flag"] == "StructureFuel":
            if asset["type_id"] == EveTypePrice.get_magmatic_gas_type_id():
                markets.set_magmatic_gases(asset["quantity"])
            elif asset["type_id"] in EveTypePrice.get_fuels_type_ids():
                fuel_blocks += asset["quantity"]
        if asset["location_flag"] == "MoonMaterialBay":
            stored_moon_material, _ = MarketsStoredMoonMaterials.objects.get_or_create(
                markets=markets, product_id=asset["type_id"]
            )
            stored_moon_material.amount = asset["quantity"]
            stored_products_to_update.append(stored_moon_material)

    markets.set_fuel_blocs(fuel_blocks)

    MarketsStoredMoonMaterials.objects.bulk_update(
        stored_products_to_update, fields=["amount"]
    )

    markets.save()


@shared_task
def update_moon(moon_id: int, update_materials: bool = False):
    """
    Update the materials and price of a Moon
    If update_materials is set to true it will look in the moonmining app to update the composition
    """
    logger.info("Updating price of moon id %s", moon_id)

    moon = Moon.objects.get(eve_moon_id=moon_id)

    moon.update_price()

    # TODO write a test for this
    if update_materials:

        create_moon_materials(moon_id)


@shared_task
def create_moon_materials(moon_id: int):
    """
    Creates the materials of a moon without materials yet
    """

    moon = Moon.objects.get(eve_moon_id=moon_id)

    harvest = get_markets_hourly_harvest(moon_id)

    # Delete all before as I have issues when using update_conflicts.
    # Backend doesn't seem compatible
    MarketsHourlyProducts.objects.filter(moon=moon).delete()
    MarketsHourlyProducts.objects.bulk_create(
        [
            MarketsHourlyProducts(moon=moon, product=goo_type, amount=amount)
            for goo_type, amount in harvest.items()
        ]
    )

    moon.update_price()


@shared_task
def update_moons_from_moonmining():
    """
    Will fetch all the moons from aa-moonmining application and update the markets database
    """

    logger.info("Updating all moons from moonmining")

    markets_moons = Moon.objects.all()
    markets_moon_ids = [moon.eve_moon.id for moon in markets_moons]
    missing_moons = MoonminingMoon.objects.exclude(eve_moon__id__in=markets_moon_ids)

    for moon in missing_moons:
        create_moon_from_moonmining.delay(moon.eve_moon.id)

    # markets moons without a moonmining moon linked
    orphan_markets_moons_ids = Moon.objects.filter(moonmining_moon=None).values_list(
        "eve_moon_id", flat=True
    )
    for moon in MoonminingMoon.objects.filter(eve_moon_id__in=orphan_markets_moons_ids):
        orphan_markets_moon = Moon.objects.get(eve_moon_id=moon.eve_moon_id)
        orphan_markets_moon.moonmining_moon = moon
        orphan_markets_moon.save()

    # creates data for moons that are missing their pulls if data is in the moonmining app
    moons_to_update = Moon.moons_in_need_of_update()
    for moon in moons_to_update:
        create_moon_materials.delay(moon.eve_moon.id)


@shared_task
def create_moon_from_moonmining(moon_id: int):
    """
    Fetches a moon from moonmining. Creates it for markets and fetches materials
    """

    logger.info("Updating materials of moon id %s", moon_id)

    Moon.objects.get_or_create(
        eve_moon_id=moon_id,
        moonmining_moon=MoonminingMoon.objects.get(eve_moon_id=moon_id),
    )

    create_moon_materials(moon_id)


@shared_task
def update_prices():
    """Task fetching prices and then updating all moon values"""

    goo_ids = EveTypePrice.get_moon_goos_type_ids()

    goo_prices = get_type_ids_prices(goo_ids)

    for type_id, price in goo_prices.items():
        type_price, _ = EveTypePrice.objects.get_or_create(
            eve_type_id=type_id,
        )
        type_price.update_price(price)

    fuel_ids = EveTypePrice.get_fuels_type_ids()
    fuel_prices = get_type_ids_prices(fuel_ids, BuySell.SELL)

    for type_id, price in fuel_prices.items():
        type_price, _ = EveTypePrice.objects.get_or_create(
            eve_type_id=type_id,
        )
        type_price.update_price(price)

    moons = Moon.objects.all()
    logger.info(
        "Successfully updated goo and fuel prices. Now updating %s moons", moons.count()
    )

    for moon in moons:
        update_moon.delay(moon.eve_moon_id)


def send_analytics(label: str, value):
    """
    Send an analytics event
    """

    logger.info("Sending analytic %s with value %s", label, value)

    analytics_event(
        namespace="markets.analytics",
        task="send_daily_stats",
        label=label,
        value=value,
        event_type="Stats",
    )


@shared_task
def send_daily_analytics():
    """
    Simple task starting the analytics work
    """

    logger.info("Starting the daily analytics task")

    count_moons = Moon.objects.count()
    count_holdings = HoldingCorporation.objects.count()
    count_markets = Markets.objects.count()

    send_analytics("moons", count_moons)
    send_analytics("holdings", count_holdings)
    send_analytics("markets", count_markets)
