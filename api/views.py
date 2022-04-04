from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
import bleach
from .models import Transcript
from django.http import JsonResponse
from .videolibrary import CHANNEL_MAPPING
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


# Create your views here.
def index(request):
    return HttpResponse("Привіт Світ! You're at the GTN Certificate Bot index.")

def transcript_list(request):
    trans = Transcript.objects.all().values('slack_user_id').distinct()
    template = loader.get_template('transcript_list.html')
    context = {
        'users': trans,
    }
    return HttpResponse(template.render(context, request))

def transcript(request, slack_user_id):
    trans = Transcript.objects.filter(slack_user_id=slack_user_id).order_by('-time')
    safetrans = [
        (x.time, x.channel, bleach.clean(x.proof), x.id)
        for x in trans
    ]
    template = loader.get_template('transcript.html')
    context = {
        'transcript': safetrans,
        'slack_user_id': slack_user_id,
        'channel_mapping': [item for sublist in CHANNEL_MAPPING.values() for item in sublist],
    }
    return HttpResponse(template.render(context, request))

def mapping(request):
    return JsonResponse(CHANNEL_MAPPING)
