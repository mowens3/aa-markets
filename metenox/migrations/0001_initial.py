# Generated by Django 4.2.15 on 2024-09-05 11:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("moonmining", "0007_add_localization"),
        ("eveuniverse", "0010_alter_eveindustryactivityduration_eve_type_and_more"),
        ("eveonline", "0017_alliance_and_corp_names_are_not_unique"),
        ("authentication", "0023_alter_userprofile_language"),
    ]

    operations = [
        migrations.CreateModel(
            name="General",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "permissions": (
                    ("basic_access", "Can access this app"),
                    (
                        "auditor",
                        "Can access metenox information about all corporations",
                    ),
                ),
                "managed": False,
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="HoldingCorporation",
            fields=[
                (
                    "corporation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        to="eveonline.evecorporationinfo",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("last_updated", models.DateTimeField(default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Metenox",
            fields=[
                (
                    "structure_id",
                    models.PositiveBigIntegerField(primary_key=True, serialize=False),
                ),
                ("structure_name", models.TextField(max_length=150)),
                ("fuel_blocks_count", models.IntegerField(default=0)),
                ("magmatic_gas_count", models.IntegerField(default=0)),
                (
                    "corporation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metenoxes",
                        to="metenox.holdingcorporation",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Metenoxes",
            },
        ),
        migrations.CreateModel(
            name="Owner",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_enabled",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Disabled corporations are excluded from the update process",
                    ),
                ),
                (
                    "character_ownership",
                    models.ForeignKey(
                        default=None,
                        help_text="Character used to sync this corporation from ESI",
                        null=True,
                        on_delete=django.db.models.deletion.SET_DEFAULT,
                        related_name="+",
                        to="authentication.characterownership",
                    ),
                ),
                (
                    "corporation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="owners",
                        to="metenox.holdingcorporation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Owner",
                "verbose_name_plural": "Owners",
            },
        ),
        migrations.CreateModel(
            name="Moon",
            fields=[
                (
                    "eve_moon",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="+",
                        serialize=False,
                        to="eveuniverse.evemoon",
                    ),
                ),
                ("value", models.FloatField(default=0)),
                ("value_updated_at", models.DateTimeField(default=None, null=True)),
                (
                    "moonmining_moon",
                    models.OneToOneField(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="moonmining.moon",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MetenoxStoredMoonMaterials",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.IntegerField(default=0)),
                (
                    "metenox",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stored_moon_materials",
                        to="metenox.metenox",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="eveuniverse.evetype",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MetenoxHourlyProducts",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.IntegerField()),
                (
                    "moon",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hourly_products",
                        to="metenox.moon",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="eveuniverse.evetype",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="metenox",
            name="moon",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="metenox",
                to="metenox.moon",
            ),
        ),
        migrations.CreateModel(
            name="EveTypePrice",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("price", models.FloatField(default=0)),
                ("last_update", models.DateTimeField(auto_now=True)),
                (
                    "eve_type",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="eveuniverse.evetype",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="metenoxstoredmoonmaterials",
            constraint=models.UniqueConstraint(
                fields=("metenox", "product"), name="functional_pk_metenoxstoredproduct"
            ),
        ),
        migrations.AddConstraint(
            model_name="metenoxhourlyproducts",
            constraint=models.UniqueConstraint(
                fields=("moon", "product"), name="functional_pk_metenoxhourlyproduct"
            ),
        ),
    ]
