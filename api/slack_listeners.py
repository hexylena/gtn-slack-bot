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
    if 'text' not in body:
        say(
            text=f":warning: Please run this command with the histories you are using as proof of completing this tutorial. E.g. /completed https://usegalaxy.../u/your-user/h/your-history\n\nWe will check these histories before granting your certificate at the end of the course.",
            ephemeral=True
        )
        return HttpResponse(status=200)

    try:
        q = Transcript(slack_user_id=body['user_id'], channel=body['channel_name'], proof=body['text'])
        q.save()
        say("Saved this course to your transcript! Congrats! You can use the command /transcript to list your transcript at any time.")
    except Exception as e:
        logger.error(e)
        say(
            text=f"Something went wrong! ({e}) We could not record your completion. Please contact <@U01F7TAQXNG>",
            ephemeral=True
        )

    return HttpResponse(status=200)


@csrf_exempt
@app.command("/transcript")
def transcript(ack, body, say):
    ack()
    logger.debug(body)

    results = Transcript.objects.filter(slack_user_id=body['user_id'])
    output = [x.channel for x in results]

    say(
        text="We have recorded you completed the following modules: " + ', '.join(output),
        ephemeral=True
    )
