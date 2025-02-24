from django.core.management.base import BaseCommand

from allianceauth.services.hooks import get_extension_logger

from metenox import tasks

logger = get_extension_logger(__name__)


class Command(BaseCommand):
    help = "Fetches new moon goo prices and update metenox harvest values"

    def handle(self, *args, **options):
        logger.info("Command to update prices received")
        tasks.update_prices.delay()
