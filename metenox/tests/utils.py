from allianceauth.eveonline.models import EveCorporationInfo

from metenox.models import HoldingCorporation


def create_test_holding(holding_id: int = 1) -> HoldingCorporation:
    """Creates a template holding corporation"""

    corporation = EveCorporationInfo.objects.create(
        corporation_id=holding_id,
        corporation_name="corporation1",
        corporation_ticker="CORP1",
        member_count=1,
    )
    holding = HoldingCorporation(corporation=corporation)
    holding.save()

    return holding
