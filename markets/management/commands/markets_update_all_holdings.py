from django.core.management.base import BaseCommand

from allianceauth.services.hooks import get_extension_logger

from markets import tasks

logger = get_extension_logger(__name__)


class Command(BaseCommand):
    help = "Update all markets holdings"

    def handle(self, *args, **options):
        logger.info("Initiating holding update tasks")
        tasks.update_all_holdings.delay()
