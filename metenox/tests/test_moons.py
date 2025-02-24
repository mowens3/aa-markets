from collections import defaultdict

from moonmining.models import Moon, MoonProduct

from django.test import TestCase
from eveuniverse.models import EveType

from metenox.models import Moon as MetenoxMoon
from metenox.moons import get_metenox_hourly_harvest

from ..tasks import create_moon_from_moonmining, update_moons_from_moonmining
from .testdata.load_eveuniverse import load_eveuniverse

MOON_ID = 40178441


class TestMoons(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_eveuniverse()

    def test_wh_moon_hourly_pull(self):
        """Hourly pull of a wormhole moon (only r4)"""
        # TODO
        self.assertTrue(True)

    def test_no_crash_querrying_moon_not_in_moonmining(self):
        """Checks that there's no error returned if you ask for a moon not in the moonmiming application"""
        get_metenox_hourly_harvest(MOON_ID)

    def test_kspace_moon_hourly_pull(self):
        """Hourly pull of an R16 moon"""
        moon_scan: dict[int, float] = {
            45501: 0.303093851,
            45497: 0.088907719,
            45499: 0.307283372,
            45490: 0.300715059,
        }

        moon, _ = Moon.objects.get_or_create(eve_moon_id=MOON_ID)
        moon_products = [
            MoonProduct(moon=moon, ore_type_id=ore_type_id, amount=ore_type_amount)
            for ore_type_id, ore_type_amount in moon_scan.items()
        ]

        moon.update_products(moon_products)

        harvest = get_metenox_hourly_harvest(moon.eve_moon_id)

        expected = defaultdict(int)
        expected.update(
            {
                EveType.objects.get(id=16634): 234,
                EveType.objects.get(id=16641): 145,
                EveType.objects.get(id=16635): 36,
                EveType.objects.get(id=16633): 36,
                EveType.objects.get(id=16644): 147,
                EveType.objects.get(id=16637): 42,
            }
        )

        self.assertDictEqual(harvest, expected)

    def test_double_r64_hourly_pull(self):
        """
        Test on a moon with double r64
        Way more moon materials present there
        """

        moon_scan = {
            45512: 0.210578531,
            45497: 0.272598475,
            45499: 0.296382815,
            45510: 0.220440164,
        }

        moon, _ = Moon.objects.get_or_create(eve_moon_id=MOON_ID)
        moon_products = [
            MoonProduct(moon=moon, ore_type_id=ore_type_id, amount=ore_type_amount)
            for ore_type_id, ore_type_amount in moon_scan.items()
        ]

        moon.update_products(moon_products)

        harvest = get_metenox_hourly_harvest(moon.eve_moon_id)

        expected = defaultdict(int)
        expected.update(
            {
                EveType.objects.get(id=16634): 52,
                EveType.objects.get(id=16640): 52,
                EveType.objects.get(id=16650): 58,
                EveType.objects.get(id=16635): 35,
                EveType.objects.get(id=16633): 50,
                EveType.objects.get(id=16644): 167,
                EveType.objects.get(id=16652): 55,
                EveType.objects.get(id=16639): 50,
                EveType.objects.get(id=16637): 130,
                EveType.objects.get(id=16642): 26,
            }
        )

        self.assertDictEqual(harvest, expected)

    def test_integrity_error_on_updating_existing_moon(self):
        """
        Integrity error issue when running an update on an already existing moon
        """

        moon_scan = {
            45490: 0.2809781134,
            45491: 0.2083230466,
            45493: 0.5106988549,
        }

        moonmining_moon, _ = Moon.objects.get_or_create(eve_moon_id=MOON_ID)
        moon_products = [
            MoonProduct(
                moon=moonmining_moon, ore_type_id=ore_type_id, amount=ore_type_amount
            )
            for ore_type_id, ore_type_amount in moon_scan.items()
        ]

        moonmining_moon.update_products(moon_products)

        create_moon_from_moonmining(MOON_ID)
        create_moon_from_moonmining(MOON_ID)

    def test_create_moon_mats_on_existing_moon(self):
        """
        When a moon is created without moon materials `create_or_update_moon_from_moonmining` needs to create them
        """

        moon_scan = {
            45490: 0.2809781134,
            45491: 0.2083230466,
            45493: 0.5106988549,
        }

        moonmining_moon, _ = Moon.objects.get_or_create(eve_moon_id=MOON_ID)
        moon_products = [
            MoonProduct(
                moon=moonmining_moon, ore_type_id=ore_type_id, amount=ore_type_amount
            )
            for ore_type_id, ore_type_amount in moon_scan.items()
        ]

        moonmining_moon.update_products(moon_products)
        metenox_moon = MetenoxMoon.objects.create(
            eve_moon_id=MOON_ID,
            moonmining_moon=moonmining_moon,
        )

        update_moons_from_moonmining()

        pull = metenox_moon.hourly_pull

        self.assertEqual(len(pull), 3)

    def test_find_moons_that_need_update(self):
        """
        Will check if it's correctly finding moons with products in the moonmining application but none in the metenox application
        """

        moon_scan = {
            45490: 0.2809781134,
            45491: 0.2083230466,
            45493: 0.5106988549,
        }

        moonmining_moon, _ = Moon.objects.get_or_create(eve_moon_id=MOON_ID)

        metenox_moon = MetenoxMoon.objects.create(
            eve_moon_id=MOON_ID,
            moonmining_moon=moonmining_moon,
        )

        moon_products = [
            MoonProduct(
                moon=moonmining_moon, ore_type_id=ore_type_id, amount=ore_type_amount
            )
            for ore_type_id, ore_type_amount in moon_scan.items()
        ]
        moonmining_moon.update_products(moon_products)

        moon_to_update = MetenoxMoon.moons_in_need_of_update()

        self.assertEqual(list(moon_to_update), [metenox_moon])

    def test_no_crash_cycles_before_full_empty_moon(self):
        """
        Checks that a moon without a survey in moonmining won't crash when cycles_before_full is called
        """

        moonmining_moon, _ = Moon.objects.get_or_create(eve_moon_id=MOON_ID)

        metenox_moon = MetenoxMoon.objects.create(
            eve_moon_id=MOON_ID,
            moonmining_moon=moonmining_moon,
        )

        metenox_moon.cycles_before_full
