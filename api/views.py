from django.shortcuts import render
from .models import Transcript
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
