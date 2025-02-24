from moonmining.models import Moon as MoonMiningMoon
from moonmining.models import MoonProduct

from django.test import TestCase
from eveuniverse.models import EveMoon, EveType

from allianceauth.eveonline.models import EveCorporationInfo

from markets.models import (
    EveTypePrice,
    HoldingCorporation,
    Metenox,
    MetenoxStoredMoonMaterials,
    MetenoxTag,
)
from markets.tasks import create_markets, update_moons_from_moonmining
from markets.tests.testdata.load_eveuniverse import load_eveuniverse

MOON_ID = 40178441


def create_test_markets() -> Metenox:
    """
    Creates a basic markets for testing purpose
    """

    corporation = EveCorporationInfo.objects.create(
        corporation_id=1,
        corporation_name="corporation1",
        corporation_ticker="CORP1",
        member_count=1,
    )
    holding = HoldingCorporation(corporation=corporation)
    holding.save()
    eve_moon = EveMoon.objects.get(id=MOON_ID)

    structure_info = {
        "name": "Metenox1",
        "structure_id": 1,
    }

    location_info = {
        "position": {
            "x": eve_moon.position_x,
            "y": eve_moon.position_y,
            "z": eve_moon.position_z,
        },
        "solar_system_id": eve_moon.eve_planet.eve_solar_system.id,
    }

    create_markets(holding.corporation.corporation_id, structure_info, location_info)

    markets = Metenox.objects.get(structure_id=1)

    return markets


class TestMetenoxes(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_eveuniverse()

    def test_moon_update_when_markets_created_on_empty_moon(self):
        """
        Check that when a markets is created on a moon that isn't present in moonmining an update will happen
        if the moon appears in moonmining
        """

        markets = create_test_markets()

        self.assertEqual(
            len(markets.moon.hourly_pull), 0
        )  # checks that the moon is empty
        self.assertEqual(markets.moon.moonmining_moon, None)

        moon_scan = {
            45490: 0.2809781134,
            45491: 0.2083230466,
            45493: 0.5106988549,
        }

        moonmining_moon, _ = MoonMiningMoon.objects.get_or_create(eve_moon_id=MOON_ID)

        moon_products = [
            MoonProduct(
                moon=moonmining_moon, ore_type_id=ore_type_id, amount=ore_type_amount
            )
            for ore_type_id, ore_type_amount in moon_scan.items()
        ]
        moonmining_moon.update_products(moon_products)

        update_moons_from_moonmining()

        self.assertEqual(
            len(markets.moon.hourly_pull), 3
        )  # checks that  the moon was updated

    def test_total_stored_volume(self):
        """Checks the volume stored in a markets"""

        markets = create_test_markets()

        atmospheric_gases = EveType.objects.get(id=16634)
        hydrocarbons = EveType.objects.get(id=16633)

        stored_atmospheric_gases = MetenoxStoredMoonMaterials(
            markets=markets, product=atmospheric_gases, amount=50
        )
        stored_atmospheric_gases.save()
        stored_hydrocarbons = MetenoxStoredMoonMaterials(
            markets=markets, product=hydrocarbons, amount=200
        )
        stored_hydrocarbons.save()

        self.assertEqual(
            markets.get_stored_moon_materials_volume(), 50 * 0.05 + 200 * 0.05
        )

    def test_total_stored_value(self):
        """Checks the value stored in a markets"""

        markets = create_test_markets()
        hydrocarbon = EveType.objects.get(id=16633)
        atmospheric_gases = EveType.objects.get(id=16634)
        EveTypePrice.objects.create(eve_type=hydrocarbon, price=2000)
        EveTypePrice.objects.create(eve_type=atmospheric_gases, price=1000)

        MetenoxStoredMoonMaterials.objects.create(
            markets=markets, product=atmospheric_gases, amount=50
        )
        MetenoxStoredMoonMaterials.objects.create(
            markets=markets, product=hydrocarbon, amount=200
        )

        self.assertEqual(
            2000 * 200 + 1000 * 50, markets.get_stored_moon_materials_value()
        )

    def test_set_fuel_blocks(self):
        """Test the set_fuel_blocks command"""

        markets = create_test_markets()
        holding = markets.corporation
        holding.ping_on_remaining_fuel_days = (
            1  # 120 fuel blocks being a daily consumption
        )
        holding.save()

        self.assertEqual(markets.fuel_blocks_count, 0)

        markets.set_fuel_blocs(1400)

        self.assertEqual(markets.fuel_blocks_count, 1400)
        self.assertFalse(markets.was_fuel_pinged)  # enough fuel to last longer

        markets.set_fuel_blocs(20)

        self.assertEqual(markets.fuel_blocks_count, 20)
        self.assertTrue(markets.was_fuel_pinged)

        markets.set_fuel_blocs(1500)

        self.assertEqual(markets.fuel_blocks_count, 1500)
        self.assertFalse(markets.was_fuel_pinged)

    def test_set_magmatic(self):
        """Test the set_magmatic command"""

        markets = create_test_markets()
        holding = markets.corporation
        holding.ping_on_remaining_magmatic_days = (
            1  # 2640 magmatic gases being a daily consumption
        )
        holding.save()

        self.assertEqual(markets.fuel_blocks_count, 0)

        markets.set_magmatic_gases(4000)

        self.assertEqual(markets.magmatic_gas_count, 4000)
        self.assertFalse(markets.was_magmatic_pinged)

        markets.set_magmatic_gases(1000)

        self.assertEqual(markets.magmatic_gas_count, 1000)
        self.assertTrue(markets.was_magmatic_pinged)

        markets.set_magmatic_gases(5000)

        self.assertEqual(markets.magmatic_gas_count, 5000)
        self.assertFalse(markets.was_magmatic_pinged)

    def test_default_tags(self):
        """
        Checks that on markets creation the default tags are correctly added
        """

        tag1 = MetenoxTag.objects.create(name="tag1", default=True)
        tag2 = MetenoxTag.objects.create(name="tag2", default=True)
        tag3 = MetenoxTag.objects.create(name="tag3")

        markets = create_test_markets()

        self.assertIn(tag1, markets.tags.all())
        self.assertIn(tag2, markets.tags.all())
        self.assertNotIn(tag3, markets.tags.all())
