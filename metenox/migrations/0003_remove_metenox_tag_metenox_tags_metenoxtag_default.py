# Generated by Django 4.2.15 on 2024-10-08 22:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("metenox", "0002_metenoxtag_alter_general_options_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="metenox",
            name="tag",
        ),
        migrations.AddField(
            model_name="metenox",
            name="tags",
            field=models.ManyToManyField(
                help_text="Tags assigned to a Metenox", to="metenox.metenoxtag"
            ),
        ),
        migrations.AddField(
            model_name="metenoxtag",
            name="default",
            field=models.BooleanField(
                default=False,
                help_text="This tag will be applied on every new metenox if true",
            ),
        ),
    ]
