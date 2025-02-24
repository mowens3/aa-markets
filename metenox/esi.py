"""
Modules containing all ESI interactions
"""

from collections import defaultdict
from typing import Dict, List, Set

from bravado.exception import HTTPForbidden

from esi.clients import EsiClientProvider
from esi.models import Token

from allianceauth.services.hooks import get_extension_logger
from app_utils.esi import fetch_esi_status

from metenox.models import HoldingCorporation

from . import __version__

METENOX_TYPE_ID = 81826

logger = get_extension_logger(__name__)

esi = EsiClientProvider(app_info_text=f"aa-metenox v{__version__}")


class ESIError(Exception):
    """Signifies that something went wrong when querying data from the ESI"""


class DownTimeError(Exception):
    """Signifies that it is currently the downtime and no data will be returned"""


def get_metenox_from_esi(
    holding_corporation: HoldingCorporation,
) -> List[Dict]:
    """Returns all metenoxes associated with a given Owner"""

    structures = get_structures_from_esi(holding_corporation)

    return [
        structure for structure in structures if structure["type_id"] == METENOX_TYPE_ID
    ]


def get_structure_info_from_esi(
    holding_corporation: HoldingCorporation, structure_id: int
) -> Dict:
    """Returns the location information of a structure"""

    for owner in holding_corporation.owners.all():

        structure_info = esi.client.Universe.get_universe_structures_structure_id(
            structure_id=structure_id,
            token=owner.fetch_token().valid_access_token(),
        ).result()

        return structure_info


def get_structures_from_esi(
    holding_corporation: HoldingCorporation,
) -> List[Dict]:
    """Returns all structures associated with a given owner"""

    if fetch_esi_status().is_daily_downtime:
        raise DownTimeError

    for owner in holding_corporation.active_owners():
        try:
            return esi.client.Corporation.get_corporations_corporation_id_structures(
                corporation_id=owner.corporation.corporation.corporation_id,
                token=owner.fetch_token().valid_access_token(),
            ).results()
        except Token.DoesNotExist:
            logger.error("No token found for owner %s when fetching assets", owner)
            owner.disable(
                cause="ESI error fetching assets. No token found for this character."
            )
        except HTTPForbidden as e:
            logger.error(
                "HTTPForbidden error when fetching holding corporation %s assets with owner %s. Error: %s",
                holding_corporation,
                owner,
                e,
            )
            owner.disable(
                cause="ESI error fetching assets. The character might not be a director."
            )
        except OSError as e:
            logger.warning(
                "Unexpected OsError when fetching holding corporation %s assets with owner %s. Error: %s",
                holding_corporation,
                owner,
                e,
            )

        continue

    raise ESIError(
        "All active owners returned exceptions when trying to get structure data"
    )


def get_corporation_assets(holding_corporation: HoldingCorporation):
    """Returns all the assets of a corporation"""

    if fetch_esi_status().is_daily_downtime:
        raise DownTimeError

    for owner in holding_corporation.active_owners():
        try:
            return esi.client.Assets.get_corporations_corporation_id_assets(
                corporation_id=holding_corporation.corporation.corporation_id,
                token=owner.fetch_token().valid_access_token(),
            ).results()
        except Token.DoesNotExist:
            logger.error("No token found for owner %s when fetching assets", owner)
            owner.disable(
                cause="ESI error fetching assets. No token found for this character."
            )
        except HTTPForbidden as e:
            logger.error(
                "HTTPForbidden error when fetching holding corporation %s assets with owner %s. Error: %s",
                holding_corporation,
                owner,
                e,
            )
            owner.disable(
                cause="ESI error fetching assets. The character might not be a director."
            )
        except OSError as e:
            logger.warning(
                "Unexpected OsError when fetching holding corporation %s assets with owner %s. Error: %s",
                holding_corporation,
                owner,
                e,
            )

        continue

    raise ESIError(
        "All active owners returned exceptions when trying to get their structure data"
    )


def get_corporation_metenox_assets(
    holding_corporation: HoldingCorporation, metenoxes_set_ids: Set[int]
) -> Dict[int, List[Dict]]:
    """
    Return the assets in the corporation's Metenoxes' MoonMaterialBay and FuelBay.
    Need to receive the set of the corporation's metenoxes ids.
    The data is formatted as a dict with the key being the metenox structure id and a list with the info
    """

    interesting_location_flags = [
        "MoonMaterialBay",
        "StructureFuel",
    ]

    holding_assets = get_corporation_assets(holding_corporation)
    assets_dic = defaultdict(list)
    for asset in holding_assets:
        if (
            asset["location_id"] in metenoxes_set_ids
            and asset["location_flag"] in interesting_location_flags
        ):
            assets_dic[asset["location_id"]].append(asset)

    return assets_dic
