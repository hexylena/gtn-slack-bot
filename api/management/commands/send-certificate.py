from django.core.management.base import BaseCommand, CommandError
import time
import requests
import tqdm
import shutil
import subprocess
import os
import tempfile
from api.videolibrary import get_course_name_and_time
from api.models import Transcript, CertificateRequest
from slack_bolt import App

TEMPLATE_SVG = os.path.join(os.path.dirname(__file__), 'template.svg')
TEMPLATE = open(TEMPLATE_SVG, 'r').read()

TEMPLATE_BACK_SVG = os.path.join(os.path.dirname(__file__), 'template-back.svg')
TEMPLATE_BACK = open(TEMPLATE_BACK_SVG, 'r').read()


if 'SENTRY_DSN' in os.environ:
    import sentry_sdk
    sentry_sdk.init(
        dsn=os.environ['SENTRY_DSN'],
        traces_sample_rate=1.0,
    )

from api.slack import app
CERTIFICATES_API_KEY = os.environ.get('CERTIFICATES_API_KEY', '')


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--slack', action='store_true', help='Send NOW via slack')

    def build_certificate_for_user(self, cert):
        cert_path = os.path.join('certs', f'{cert.human_name}.pdf')
        if os.path.exists(cert_path):
            return cert_path

        # cert = CertificateRequest.objects.get(slack_user_id=user_id)
        print(cert.transcript_items)

        response = requests.post('https://certificates.apps.galaxyproject.eu/certificate', json={
            'name': cert.human_name,
            'modules': [
                f"{v}: {k}"
                for (k, v) in
                cert.transcript_items.items()
            ],
            'ects': cert.total_ects,
        }, headers={
            'Authorization': CERTIFICATES_API_KEY
        })

        # if it was successful
        if response.status_code == 200:
            with open(cert_path, 'wb') as handle:
                handle.write(response.content)
            return cert_path
        else:
            print(response.text)
            raise Exception("Could not generate certificate")


    def generate_rejection_text(self, cert):
        text = f"""Hello <@{cert.slack_user_id}>! Unfortunately we could not verify your certificate submissions, they may be inaccessible or deleted. If you think this is in error, please contact us\n\nHere is a list of the submissions you provided which we could not verify:\n"""
        transcript = Transcript.objects.filter(slack_user_id=cert.slack_user_id)
        for t in transcript:
            text += f"- {t.proof} ({t.channel})\n"
        text += "\n:robot_face: I am a bot account and do not read responses, anything you write to me will be lost. To talk to a human please write in <#C032C2MRHAS>"
        return text

    def handle(self, *args, **options):
        for cert in tqdm.tqdm(CertificateRequest.objects.filter(approved='REJ').order_by('slack_user_id')):
            text = self.generate_rejection_text(cert)
            print(f"=== Rejecting {cert} ===")
            print(text)

            if options['slack']:
                try:
                    print(app.client.chat_postMessage(channel=cert.slack_user_id, text=text))
                    cert.approved = 'R/S'
                    cert.save()
                    time.sleep(1)
                except Exception as e:
                    print(e)
                    print("Error sending message")

        for cert in tqdm.tqdm(CertificateRequest.objects.filter(approved='ACC').order_by('slack_user_id')):
            print(cert.slack_user_id)
            # user_id = 'U01F7TAQXNG'
            file_path = self.build_certificate_for_user(cert)

            if options['slack']:
                try:
                    upload = app.client.files_upload(file=file_path, filename=f'certificate-{cert.slack_user_id}.pdf')
                    message = "Congratulations! Please find your certificate below."
                    message += "<"+upload['file']['permalink']+"| >"
                    message += ":robot_face: I am a bot account and do not read responses, anything you write to me will be lost. To talk to a human please write in <#C032C2MRHAS>"
                    message += ":warning: Please download this certificate soon, as it may be eventually removed from Slack. If you lose access to it, you can later download it from <https://drive.google.com/drive/folders/1J2gY8xgYMceUkcpouZeNYqnAr0XvEBvt?usp=sharing|Google Drive>"
                    print(app.client.chat_postMessage(channel=cert.slack_user_id, text=message))
                    time.sleep(2)

                    # Mark it as sent, successful.
                    cert.approved = 'S/S'
                    cert.save()

                except Exception as e:
                    print(e)
                    print("Error sending message")
