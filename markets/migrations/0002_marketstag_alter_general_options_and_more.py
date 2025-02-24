# Generated by Django 4.2.15 on 2024-10-07 11:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("markets", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MetenoxTag",
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
                ("name", models.CharField(max_length=20)),
            ],
        ),
        migrations.AlterModelOptions(
            name="general",
            options={
                "default_permissions": (),
                "managed": False,
                "permissions": (
                    ("view_moons", "Can see all scanned moons"),
                    (
                        "view_markets",
                        "Can add owners and view related corporations markets",
                    ),
                    ("corporation_manager", "Can modify a corporation ping settings"),
                    (
                        "auditor",
                        "Can access markets information about all corporations",
                    ),
                ),
            },
        ),
        migrations.AddField(
            model_name="holdingcorporation",
            name="ping_on_remaining_fuel_days",
            field=models.IntegerField(
                default=0,
                help_text="Ping should be sent when the fuel blocks stored in a Markets allow less than this value",
            ),
        ),
        migrations.AddField(
            model_name="holdingcorporation",
            name="ping_on_remaining_magmatic_days",
            field=models.IntegerField(
                default=0,
                help_text="Ping should be sent when the magmatic gases stored in a Markets allow less than this value",
            ),
        ),
        migrations.AddField(
            model_name="markets",
            name="was_fuel_pinged",
            field=models.BooleanField(
                default=False,
                help_text="If a ping has been sent out after noticing a low fuel level",
            ),
        ),
        migrations.AddField(
            model_name="markets",
            name="was_magmatic_pinged",
            field=models.BooleanField(
                default=False,
                help_text="If a ping has been sent out after noticing a low magmatic level",
            ),
        ),
        migrations.CreateModel(
            name="Webhook",
            fields=[
                (
                    "webhook_id",
                    models.BigIntegerField(primary_key=True, serialize=False),
                ),
                ("webhook_token", models.TextField()),
                (
                    "name",
                    models.CharField(
                        help_text="Text to recognize the webhook",
                        max_length=30,
                        unique=True,
                    ),
                ),
                (
                    "default",
                    models.BooleanField(
                        default=False,
                        help_text="If the webhook will automatically be added to every new corporation",
                    ),
                ),
                (
                    "holding_corporations",
                    models.ManyToManyField(
                        help_text="Corporation associated to this webhook",
                        related_name="webhooks",
                        to="markets.holdingcorporation",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="markets",
            name="tag",
            field=models.ForeignKey(
                default=None,
                help_text="Tag assigned to a Markets",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="markets.marketstag",
            ),
        ),
    ]
