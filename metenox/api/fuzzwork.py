"""Interactions with the fuzzwork market API"""

from enum import Enum
from typing import Dict, List

import requests

from eveuniverse.models import EveType

from allianceauth.services.hooks import get_extension_logger

from metenox import __version__, repo_url

FUZZWORK_URL = "https://market.fuzzwork.co.uk/aggregates/"
THE_FORGE_REGION_ID = 10000002

logger = get_extension_logger(__name__)


class BuySell(Enum):
    """Parameter to see if you want to fetch buy or sell orders"""

    BUY = "buy"
    SELL = "sell"


class PriceType(Enum):
    """Parameter to know what price aggregate you're looking for"""

    WEIGHTED_AVERAGE = "weightedAverage"
    MAX = "max"
    MIN = "min"
    MEDIAN = "median"
    FIVE_PERCENT_WEIGHTED_AVERAGE = "percentile"


def get_types_prices(
    eve_types: List[EveType], buy_sell: BuySell, price_type: PriceType
) -> Dict[int, float]:
    """
    Retrieves the price of the given eve_types from the Fuzzwork API
    The parameters allow to select the  price type you want
    """

    type_ids = [eve_type.id for eve_type in eve_types]
    return get_type_ids_prices(type_ids, buy_sell, price_type)


def get_type_ids_prices(
    eve_types_ids: List[int],
    buy_sell: BuySell = BuySell.BUY,
    price_type: PriceType = PriceType.FIVE_PERCENT_WEIGHTED_AVERAGE,
) -> Dict[int, float]:
    """
    Retrieves the price of the given eve_type_ids from the Fuzzwork API
    The parameters allow to select the  price type you want
    """

    if not eve_types_ids:
        logger.warning("Received an empty list for fetching prices")
        return {}

    url = f"{FUZZWORK_URL}?region={THE_FORGE_REGION_ID}&types={','.join([str(eve_type_id) for eve_type_id in eve_types_ids])}"

    user_agent = f"aa-metenox v{__version__} {repo_url}"

    logger.info("Trying to fetch data from %s" % url)
    r = requests.get(url, headers={"User-Agent": user_agent}, timeout=5)
    r.raise_for_status()

    output_dic = {}

    for type_id, market_info in r.json().items():
        output_dic[int(type_id)] = float(market_info[buy_sell.value][price_type.value])

    return output_dic
