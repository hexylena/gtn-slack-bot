from django.core.management.base import BaseCommand, CommandError
from api.models import Transcript, CertificateRequest


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
