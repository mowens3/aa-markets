from django.core.management import BaseCommand, call_command

from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


class Command(BaseCommand):
    help = "Preload static data from the ESI"

    def handle(self, *args, **options):
        call_command(
            "eveuniverse_load_types",
            "metenox",
            "--group_id",
            427,  # moon goo
            "--group_id",
            1136,  # fuel block
            "--type_id",
            81143,  # magmatic
        )

        """
        self.stdout.write("Loading data from the ESI. It might take a while")
        goo_types_count = EveType.objects.filter(eve_group_id=25).count()
        self.stdout.write(f"Already {goo_types_count} in the database.")
        self.stdout.write()
        user_input = input("Do you want to proceed? (y/N)?")

        if user_input.lower() == "y":
            self.stdout.write("Starting to fetch moon goos")
            update_or_create_eve_object.delay(
                model_name="EveType",
                id=25,
                enabled_sections=[
                    EveType.Section.DOGMAS,
                    EveType.Section.TYPE_MATERIALS,
                ],
            )

            self.stdout.write("Done")

        else:
            self.stdout.write("Aborted")
        """
