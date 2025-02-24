from django.core.management.base import BaseCommand

from allianceauth.services.hooks import get_extension_logger

from metenox import tasks

logger = get_extension_logger(__name__)


class Command(BaseCommand):
    help = (
        "Fetches all moons from moonining application and adds them to this application"
    )

    def handle(self, *args, **options):
        tasks.update_moons_from_moonmining.delay()
