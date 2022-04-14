from django.core.management.base import BaseCommand, CommandError
import time
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

    def build_certificate_for_user(self, cert):
        if os.path.exists(f'certs/{cert.human_name}.pdf'):
            return f'certs/{cert.human_name}.pdf'

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
            formatted_time = str(uniq_items[t])
            parts = formatted_time.split(':')
            final_parts = ""
            if int(parts[0]) != 0:
                final_parts += f'{parts[0]}h'
            if int(parts[1]) != 0:
                final_parts += f'{parts[1]}m'

            transcript_text += f'<flowPara id="courses.{i}">{t} ({final_parts})</flowPara>'

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

        # Final cleanup
        final_pdf.close()
        os.unlink(final_pdf.name)

        return f'certs/{cert.human_name}.pdf'

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

        for cert in tqdm.tqdm(CertificateRequest.objects.filter(approved='ACK').order_by('slack_user_id')):
            print(cert.slack_user_id)
            # user_id = 'U01F7TAQXNG'
            file_path = self.build_certificate_for_user(cert)

            if options['slack']:
                try:
                    upload = app.client.files_upload(file=file_path, filename=f'certificate-{cert.slack_user_id}.pdf')
                    message = "Congratulations on attending GTN Tapas! Please find your certificate below."
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
