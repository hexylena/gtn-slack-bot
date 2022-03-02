import logging
from .models import Transcript
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import os

from slack_bolt import App

logger = logging.getLogger(__name__)

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    # disable eagerly verifying the given SLACK_BOT_TOKEN value
    token_verification_enabled=True,
)


@app.event("app_mention")
def handle_app_mentions(logger, event, say):
    logger.info(event)
    say(f"Hi there, <@{event['user']}>")

@csrf_exempt
@app.command("/completed")
def completed(ack, body, logger, say):
    ack()
    logger.debug(body)
    try:
        q = Transcript(slack_user_id=body['user_id'], channel=body['channel_name'], proof=body['text'])
        q.save()
        say("Saved!")

    except Exception as e:
        logger.error(e)
        say(f"Something went wrong! ({e}) We could not record your completion. Please contact <@U01F7TAQXNG>")

    return HttpResponse(status=200)
