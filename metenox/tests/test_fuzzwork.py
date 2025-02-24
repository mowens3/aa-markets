import responses

from django.test import TestCase
from eveuniverse.models import EveType

from metenox.api.fuzzwork import get_type_ids_prices
from metenox.models import EveTypePrice
from metenox.tests.testdata.load_eveuniverse import load_eveuniverse


class TestFuzzWork(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_eveuniverse()

    def test_crash_empty_search_query(self):
        """
        With an empty search query the API returns [] instead of a dict.
        This makes the code crash whe calling .items() on the result
        """

        get_type_ids_prices([])

    def test_no_price_update_on_zero(self):
        """
        If the new price of an eve type is zero it is refused
        """

        eve_type = EveType.objects.get(id=16634)
        type_price = EveTypePrice.objects.create(eve_type=eve_type, price=10_000)

        type_price.update_price(0)

        self.assertEqual(type_price.price, 10_000)

    @responses.activate
    def test_price_update(self):
        """
        The update_price method of EveTypePrice was crashing because fuzzwork api returned strings insteaf of float
        """

        eve_type = EveType.objects.get(id=16634)
        type_price = EveTypePrice.objects.create(eve_type=eve_type, price=100)

        responses.add(
            responses.GET,
            "https://market.fuzzwork.co.uk/aggregates/?region=10000002&types=16634",
            json={
                "16634": {
                    "buy": {
                        "weightedAverage": "3.6472570077758157",
                        "max": "6.0",
                        "min": "1.0",
                        "stddev": "1.0075961492582244",
                        "median": "4.01",
                        "volume": "9217403417.0",
                        "orderCount": "50",
                        "percentile": "4.48628743026839",
                    },
                    "sell": {
                        "weightedAverage": "7.128700104959353",
                        "max": "49990.0",
                        "min": "4.59",
                        "stddev": "5660.896280924974",
                        "median": "5.625",
                        "volume": "8841046323.0",
                        "orderCount": "78",
                        "percentile": "5.0194735444105",
                    },
                }
            },
            status=200,
        )

        new_price = get_type_ids_prices([16634])
        self.assertEqual(new_price[16634], 4.48628743026839)

        type_price.update_price(new_price[16634])

        self.assertEqual(type_price.price, 4.48628743026839)
