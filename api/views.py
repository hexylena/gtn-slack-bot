from django.shortcuts import render
from .models import Transcript
from django.http import HttpResponse
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

@app.command("/completed")
def handle_completed(ack, body, logger, say):
    ack()
    try:
        q = Transcript(slack_user_id=body['user_id'], channel=body['channel_name'], proof=body['text'])
        q.save()
        say("Saved!")

    except Exception as e:
        print(e)
        say("Something went wrong! We could not record your completion. Please contact <@U01F7TAQXNG>")
