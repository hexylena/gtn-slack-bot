from django.core.management.base import BaseCommand, CommandError
import shutil
import subprocess
import os
import tempfile
from api.videolibrary import get_course_name
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
        pass

    def build_certificate_for_user(self, user_id):
        cert = CertificateRequest.objects.get(slack_user_id=user_id)
        transcript = Transcript.objects.filter(slack_user_id=user_id, valid=True)

        cert_svg = tempfile.NamedTemporaryFile(delete=False, suffix='.svg')
        cert_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        transcript_svg = tempfile.NamedTemporaryFile(delete=False, suffix='.svg')
        transcript_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        final_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')

        # Generate our transcript text
        transcript_text = ""
        for i, t in enumerate(transcript):
            transcript_text += f'<flowPara id="courses.{i}">{get_course_name(t.channel)}</flowPara>'

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

        # upload = app.client.files_upload(file=final_pdf.name, filename=f'certificate-{user_id}.pdf')
        # message = "Congratulations on attending GTN Tapas! Please find your certificate below."
        # message += "<"+upload['file']['permalink']+"| >"
        # print(app.client.chat_postMessage(channel=user_id, text=message))

        # Final cleanup
        final_pdf.close()
        os.unlink(final_pdf.name)

    def handle(self, *args, **options):
        # Hardcode for now
        user_id = 'U01F7TAQXNG'
        self.build_certificate_for_user(user_id)
