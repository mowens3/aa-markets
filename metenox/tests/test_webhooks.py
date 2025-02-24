from django.test import TestCase

from metenox.models import Webhook
from metenox.tests.testdata.load_eveuniverse import load_eveuniverse
from metenox.tests.utils import create_test_holding


class TestWebhooks(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_eveuniverse()

    def test_parse_webhook(self):
        """Parses a correct webhook and gets information"""

        holding_corporation = create_test_holding()

        webhook_url = "https://discord.com/api/webhooks/1105231532688192/1uR8aOH95dvZoGUpIdqwKed2z3R2rwH-JNdwDw2hP_IaYeuJnDDdwq41IBfQkBm5GKR_AApfv"

        webhook = Webhook.create_from_url(webhook_url, holding_corporation)

        self.assertIsNotNone(webhook)
        self.assertEqual(webhook.webhook_id, 1105231532688192)
        self.assertEqual(
            webhook.webhook_token,
            "1uR8aOH95dvZoGUpIdqwKed2z3R2rwH-JNdwDw2hP_IaYeuJnDDdwq41IBfQkBm5GKR_AApfv",
        )
        self.assertIn(holding_corporation, webhook.holding_corporations.all())
        self.assertEqual(webhook, Webhook.objects.all()[0])
        self.assertEqual(webhook.name, "")

    def test_parse_webhook_with_name(self):
        """Parses a correct webhook and its name then gets information"""

        holding_corporation = create_test_holding()

        webhook_url = "https://discord.com/api/webhooks/1105231532688192/1uR8aOH95dvZoGUpIdqwKed2z3R2rwH-JNdwDw2hP_IaYeuJnDDdwq41IBfQkBm5GKR_AApfv"

        webhook = Webhook.create_from_url(webhook_url, holding_corporation, "test_name")

        self.assertIsNotNone(webhook)
        self.assertEqual(webhook.webhook_id, 1105231532688192)
        self.assertEqual(
            webhook.webhook_token,
            "1uR8aOH95dvZoGUpIdqwKed2z3R2rwH-JNdwDw2hP_IaYeuJnDDdwq41IBfQkBm5GKR_AApfv",
        )
        self.assertIn(holding_corporation, webhook.holding_corporations.all())
        self.assertEqual(webhook, Webhook.objects.all()[0])
        self.assertEqual(webhook.name, "test_name")

    def test_parse_webhook_error(self):
        """Parses an incorrect webhook that will return a None"""

        holding_corporation = create_test_holding()

        webhook_url = "https://discord.co/adwpi/webhok/1105231532688192/1uR8aOH95dvZoGUpIdqwKed2z3R2rwH-JNdwDw2hP_IaYeuJnDDdwq41IBfQkBm5GKR_AApfv"

        webhook = Webhook.create_from_url(webhook_url, holding_corporation)

        self.assertIsNone(webhook)

    def test_build_url(self):
        """Checks that URLs are built as expected"""

        holding_corporation = create_test_holding()

        webhook_url = "https://discord.com/api/webhooks/1105231532688192/1uR8aOH95dvZoGUpIdqwKed2z3R2rwH-JNdwDw2hP_IaYeuJnDDdwq41IBfQkBm5GKR_AApfv"

        webhook = Webhook.create_from_url(webhook_url, holding_corporation)

        self.assertEqual(webhook.url, webhook_url)

    def test_add_default_webhooks(self):
        """Checks if default webhooks are properly applied"""

        webhook1 = Webhook.objects.create(
            webhook_id=1, webhook_token="a", name="webhook1", default=True
        )
        webhook2 = Webhook.objects.create(
            webhook_id=2, webhook_token="b", name="webhook2", default=True
        )
        webhook3 = Webhook.objects.create(
            webhook_id=3, webhook_token="c", name="webhook3", default=False
        )

        holding_corporation = create_test_holding()

        Webhook.add_default_webhooks_to_corporation(holding_corporation)

        corporation_webhooks = holding_corporation.webhooks.all()

        self.assertIn(webhook1, corporation_webhooks)
        self.assertIn(webhook2, corporation_webhooks)
        self.assertNotIn(webhook3, corporation_webhooks)
