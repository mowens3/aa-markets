from django.core.management.base import BaseCommand

from allianceauth.services.hooks import get_extension_logger

from markets import tasks

logger = get_extension_logger(__name__)


class Command(BaseCommand):
    help = "Fetches new moon goo prices and update markets harvest values"

    def handle(self, *args, **options):
        logger.info("Command to update prices received")
        tasks.update_prices.delay()
