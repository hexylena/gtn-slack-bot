from django.core.management.base import BaseCommand, CommandError
import json
import time
import os
from api.models import ScheduledMessage
from api.slack import app
from api.utils import convert_text
from api.build import template_messages
from django.utils import timezone


if 'SENTRY_DSN' in os.environ:
    import sentry_sdk
    sentry_sdk.init(
        dsn=os.environ['SENTRY_DSN'],
        traces_sample_rate=1.0,
    )

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('start', type=str, help="Start date of the event (required format: YYYY-mm-ddThh:mm:ss)")
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--zones', type=str, nargs='+',
                            help='A list of timezones to use', default=['Pacific/Auckland', 'Europe/Amsterdam', 'America/New_York'])
        parser.add_argument('--days', type=int, help="Number of days of the event", default=5)
        parser.add_argument('--channel', type=str, help="Channel to send a message to, can be human readable with # or C....", default="#testing")

    def handle(self, *args, **options):
        start = datetime.strptime(options['start'], '%Y-%m-%dT%H:%M:%S')
        template_messages(options['channel'], options['zones'], start, days=options['days'], dry_run=options['dry_run'])
