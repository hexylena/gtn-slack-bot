# Generated by Django 4.2.1 on 2023-05-25 08:06

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0010_gratitude"),
    ]

    operations = [
        migrations.RenameField(
            model_name="gratitude",
            old_name="slack_channel_human",
            new_name="slack_channel_id",
        ),
    ]
