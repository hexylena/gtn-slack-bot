from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import loader
import bleach
from api.models import Transcript, CertificateRequest
from django.http import JsonResponse
from api.videolibrary import CHANNEL_MAPPING
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from slack_bolt import App
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

# Create your views here.
def index(request):
    template = loader.get_template('index.html')
    return HttpResponse(template.render({}, request))

def transcript_list(request):
    trans = CertificateRequest.objects.all().order_by('slack_user_id')
    template = loader.get_template('transcript_list.html')
    context = {
        'users': trans,
    }
    return HttpResponse(template.render(context, request))

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
        cr.approved = True
        cr.save()
        return redirect('transcript_list')


    trans = Transcript.objects.filter(slack_user_id=slack_user_id).order_by('-time')
    safetrans = [
        (x.time, x.channel, '<br>'.join([f'<a href="{x}">{x}</a>' for x in bleach.clean(x.proof).split()]) , x.id, probably_hist(x.proof), x.valid)
        for x in trans
    ]
    template = loader.get_template('transcript.html')
    context = {
        'transcript': safetrans,
        'slack_user_id': slack_user_id,
        'channel_mapping': list(set(sorted([item for sublist in CHANNEL_MAPPING.values() for item in sublist]))),
        'message': None,
    }
    return HttpResponse(template.render(context, request))

def mapping(request):
    return JsonResponse(CHANNEL_MAPPING, json_dumps_params={'indent': 2})
