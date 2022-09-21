import json
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import loader
import bleach
from api.models import Transcript, CertificateRequest
from django.http import JsonResponse
from api.videolibrary import CHANNEL_MAPPING
from slack_bolt import App
from django.views.decorators.csrf import csrf_exempt
import os
import logging

logger = logging.getLogger(__name__)

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token_verification_enabled=True,
)


def probably_hist(text):
    return '/u/' in text and ('/h/' in text or '/w/' in text)


def template(name, request, context=None):
    if context is None:
        context = {}

    template = loader.get_template(name)
    context.update({
        'GIT_REVISION': settings.GIT_REVISION,
    })
    return HttpResponse(template.render(context, request))


def index(request):
    return template('index.html', request)


def transcript_list(request):
    trans = CertificateRequest.objects.all().order_by('slack_user_id')
    done = 0
    if len(trans) > 0:
        done = 100 * len([x.approved for x in trans if x.approved != 'UNK']) / len(trans)
    context = {
        'users': trans,
        'done': done
    }
    return template('transcript_list.html', request, context)


@csrf_exempt
def send_message_to_channel(request, channel_id):
    if channel_id != 'C01PQ3P2TTL':
        return HttpResponse("Testing only.", status=403)

    if request.method != 'POST':
        return

    blocks = json.loads(request.body)
    try:
        app.client.conversations_join(channel=channel_id)
    except:
        return HttpResponse("Could not join conversation", status=500)

    app.client.chat_postMessage(
        channel=channel_id,
        blocks=blocks
    )
    return HttpResponse("Done")


def transcript(request, slack_user_id):
    if request.method == 'POST':
        results = {}
        for k, v in request.POST.items():
            if not (k.startswith('valid') or k.startswith("actual_course")):
                continue

            # Parse out the identifiers
            type, cid = k.split('.')
            cid = int(cid)

            if cid not in results:
                results[cid] = {}

            if type == 'valid':
                results[cid]['valid'] = True
            elif type == 'actual_course':
                results[cid]['course'] = v

        results_valid = {k: v for k, v in results.items() if v.get('valid', False) == True}
        results_invalid = {k: v for k, v in results.items() if v.get('valid', False) == False}

        for k, v in results_valid.items():
            t = Transcript.objects.get(id=k)
            t.valid = True
            t.channel = v['course']
            t.save()

        for k, v in results_invalid.items():
            t = Transcript.objects.get(id=k)
            t.valid = False
            t.channel = v['course']
            t.save()

        cr = CertificateRequest.objects.filter(slack_user_id=slack_user_id).get()
        cr.approved = 'ACC' if request.POST['decision'] == 'ACC' else 'REJ'
        cr.save()
        return redirect('transcript_list')


    trans = Transcript.objects.filter(slack_user_id=slack_user_id).order_by('-time')
    safetrans = [
        (x.time, x.channel, bleach.clean('<br>'.join([f'<a href="{x}">{x}</a>' for x in bleach.clean(x.proof).split()])) , x.id, probably_hist(x.proof), x.valid)
        for x in trans
    ]
    context = {
        'transcript': safetrans,
        'slack_user_id': slack_user_id,
        'channel_mapping': sorted(list(set(sorted([item for sublist in CHANNEL_MAPPING.values() for item in sublist])))),
        'message': None,
    }
    return template('transcript.html', request, context)

def mapping(request):
    return JsonResponse(CHANNEL_MAPPING, json_dumps_params={'indent': 2})
