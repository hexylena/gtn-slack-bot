from django.shortcuts import render
from django.http import HttpResponse
from slack_bolt import App
import os

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    # signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    # disable eagerly verifying the given SLACK_BOT_TOKEN value
    token_verification_enabled=False,
)


# Create your views here.
def index(request):
    return HttpResponse("Привіт Світ! You're at the GTN Certificate Bot index.")

# def completed(request):
    # return HttpResponse("Hello, world. You're at the polls index.")
    # try:
        # msg = processCompleted(body['user_id'], body['channel_name'], body['text'])
        # ack(msg)
    # except Exception as e:
        # logger(e)
        # ack("Something went wrong! We could not record your completion. Please contact <@U01F7TAQXNG>")
