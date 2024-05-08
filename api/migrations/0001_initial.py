# Generated by Django 4.2.1 on 2023-09-29 10:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("start", models.DateTimeField()),
                ("end", models.DateTimeField()),
                ("end_grace", models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name="EventOrganiser",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("human_name", models.CharField(max_length=32, null=True)),
                ("events", models.ManyToManyField(to="api.event")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SlackUser",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slack_user_id", models.CharField(max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "current_event",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.event",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Transcript",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("time", models.DateTimeField(auto_now_add=True)),
                ("channel", models.TextField()),
                ("proof", models.TextField()),
                ("valid", models.BooleanField(default=False)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.event"
                    ),
                ),
                (
                    "slack_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.slackuser"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ScheduledMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slack_channel_id", models.CharField(max_length=32)),
                ("scheduled_for", models.DateTimeField()),
                ("message", models.TextField()),
                ("sent", models.DateTimeField(blank=True, null=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.event"
                    ),
                ),
                (
                    "scheduled_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.eventorganiser",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Gratitude",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("message", models.TextField()),
                ("date", models.DateTimeField()),
                ("slack_channel_id", models.CharField(max_length=64)),
                ("slack_channel_name", models.CharField(max_length=64)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.event"
                    ),
                ),
                (
                    "slack_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.slackuser"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CertificateRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("human_name", models.CharField(max_length=64)),
                ("course", models.TextField()),
                (
                    "approved",
                    models.CharField(
                        choices=[
                            ("ACC", "Accepted"),
                            ("REJ", "Rejected"),
                            ("UNK", "Unknown"),
                            ("S/S", "Certificate Sent"),
                            ("R/S", "Rejection Sent"),
                        ],
                        default="UNK",
                        max_length=3,
                    ),
                ),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.event"
                    ),
                ),
                (
                    "slack_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.slackuser"
                    ),
                ),
            ],
        ),
    ]
