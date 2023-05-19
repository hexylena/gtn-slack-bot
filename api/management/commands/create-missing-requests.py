from django.core.management.base import BaseCommand, CommandError
import time
import os
from api.models import Transcript, CertificateRequest
from slack_bolt import App

if 'SENTRY_DSN' in os.environ:
    import sentry_sdk
    sentry_sdk.init(
        dsn=os.environ['SENTRY_DSN'],
        traces_sample_rate=1.0,
    )

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN", ""),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
    token_verification_enabled=True,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        for user in Transcript.objects.all().values('slack_user_id').distinct():
            existing_requests = CertificateRequest.objects.filter(
                slack_user_id=user['slack_user_id'],
            )
            print(user, len(existing_requests))
            if len(existing_requests) == 0:
                q = CertificateRequest(
                    slack_user_id=user['slack_user_id'],
                    human_name=user['slack_user_id'],
                    course="GTN Tapas",
                    approved=False,
                )
                q.save()

        # Delete duplicate CRs
        for cr in CertificateRequest.objects.all():
            courses_completed = Transcript.objects.filter(slack_user_id=cr.slack_user_id)
            if len(courses_completed) == 0:
                cr.delete()

        # Fix human names
        for cr in CertificateRequest.objects.all():
            if (cr.human_name == cr.slack_user_id and cr.slack_user_id.startswith('U')) or '://' in cr.human_name:
                info = app.client.users_info(user=cr.slack_user_id).data

                # Sometimes users won't use the real name, and instead display
                # name or another field!
                potential_names = [
                    info['user']['real_name'],
                    info['user']['name'],
                    info['user']['profile']['display_name'],
                ]
                # So we use this "Great" metric of whichever is longer as their
                # probable full name.
                longer = sorted(potential_names, key=lambda x: -len(x))
                cr.human_name = longer[0]
                cr.save()
                time.sleep(2)
