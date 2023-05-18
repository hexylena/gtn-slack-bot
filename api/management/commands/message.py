from django.core.management.base import BaseCommand, CommandError
import json
import time
import os
from api.models import ScheduledMessage
from api.slack import app
from api.utils import convert_text
from django.utils import timezone


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        for message in ScheduledMessage.objects.filter(sent=None):
            now = timezone.now()

            # Could probably happen in DB, eh?
            if message.scheduled_for < now:
                print(f"Sending {message.id} {message.slack_channel_id} {message.scheduled_for}")
                blocks = convert_text(message.message)

                if options['dry_run']:
                    print(json.dumps(blocks, indent=2))
                    continue

                result = app.client.chat_postMessage(
                    channel=message.slack_channel_id,
                    text=message.message,
                    blocks=blocks['blocks'],
                )
                print(result)

                # Assuming the above worked, mark it as sent
                message.sent = now
                message.save()
