from django.core.management.base import BaseCommand, CommandError
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

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN", ""),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
    token_verification_enabled=True,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--slack', action='store_true', help='Send NOW via slack')

    def build_certificate_for_user(self, cert, slack=False):
        if os.path.exists(f'certs/{cert.human_name}.pdf'):
            return

        # cert = CertificateRequest.objects.get(slack_user_id=user_id)
        user_id = cert.slack_user_id
        transcript = Transcript.objects.filter(slack_user_id=user_id, valid=True)

        cert_svg = tempfile.NamedTemporaryFile(delete=False, suffix='.svg')
        cert_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        transcript_svg = tempfile.NamedTemporaryFile(delete=False, suffix='.svg')
        transcript_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        final_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')

        uniq_items = dict([
            get_course_name_and_time(t.channel) for t in transcript
        ])
        print(uniq_items)

        # Generate our transcript text
        transcript_text = ""
        for i, t in enumerate(sorted(uniq_items.keys())):
            transcript_text += f'<flowPara id="courses.{i}">{t} - {uniq_items[t]}</flowPara>'

        # Front side of cert
        cert_svg.write(TEMPLATE.replace('NAME', cert.human_name).encode())
        cert_svg.close()
        subprocess.check_call([
            'convert', '-density', '200', cert_svg.name, cert_pdf.name
        ])
        os.unlink(cert_svg.name)

        # Back side of cert
        transcript_svg.write(TEMPLATE_BACK.replace('<flowPara id="COURSES">COURSES</flowPara>', transcript_text).encode())
        transcript_svg.close()
        subprocess.check_call([
            'convert', '-density', '200', transcript_svg.name, transcript_pdf.name
        ])
        os.unlink(transcript_svg.name)

        # Merge our two PDFs
        subprocess.check_call([
            'gs', '-dBATCH', '-dNOPAUSE', '-q', '-sDEVICE=pdfwrite', f'-sOutputFile={final_pdf.name}', cert_pdf.name, transcript_pdf.name
        ])
        # Cleanup asap
        cert_pdf.close()
        transcript_pdf.close()
        os.unlink(cert_pdf.name)
        os.unlink(transcript_pdf.name)

        # Upload
        shutil.copyfile(final_pdf.name, f'certs/{cert.human_name}.pdf')

        if slack:
            upload = app.client.files_upload(file=final_pdf.name, filename=f'certificate-{user_id}.pdf')
            message = "Congratulations on attending GTN Tapas! Please find your certificate below."
            message += "<"+upload['file']['permalink']+"| >"
            message += ":robot_face: I am a bot account and do not read responses, anything you write to me will be lost. To talk to a human please write in #general."
            print(app.client.chat_postMessage(channel=user_id, text=message))

        # Final cleanup
        final_pdf.close()
        os.unlink(final_pdf.name)

        # Mark it as sent, successful.
        cert.approved = 'S/S'
        cert.save()

    def handle(self, *args, **options):
        # Hardcode for now
        for cert in tqdm.tqdm(CertificateRequest.objects.filter(approved='S/S').order_by('slack_user_id')):
            print(cert.slack_user_id)
            # user_id = 'U01F7TAQXNG'
            self.build_certificate_for_user(cert, slack=options['slack'])
