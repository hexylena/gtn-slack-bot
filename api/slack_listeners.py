import logging
import random
import uuid
from .models import Transcript
from django.http import HttpResponse
from .videolibrary import CHANNEL_MAPPING
from django.views.decorators.csrf import csrf_exempt
import json
import os


__import__('pprint').pprint(CHANNEL_MAPPING)

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
@app.command("/debug")
def debug(ack, body, logger, say):
    ack()
    say(f"{body}")


def ephemeral(client, body, message):
    client.chat_postEphemeral(
        channel=body['channel_id'],
        user=body['user_id'],
        text=message,
    )


@csrf_exempt
@app.command("/completed")
def completed(ack, body, logger, say, client):
    ack()
    if 'text' not in body:
        ephemeral(client, body, f":warning: Please run this command with the histories you are using as proof of completing this tutorial. E.g. /completed https://usegalaxy.../u/your-user/h/your-history\n\nWe will check these histories before granting your certificate at the end of the course.")
        return HttpResponse(status=200)

    if body['channel_name'] not in CHANNEL_MAPPING:
        ephemeral(client, body, f"This channel is not associated with a course module. If you believe this is an error, please contact <@U01F7TAQXNG>")
        return HttpResponse(status=200)

    real_module = CHANNEL_MAPPING[body['channel_name']]
    if len(real_module) == 1:
        module = real_module[1]
    else:
        module = 'channel:' + body['channel_name']

    try:
        q = Transcript(slack_user_id=body['user_id'], channel=module, proof=body['text'])
        q.save()
        ephemeral(client, body, f"Saved this course to your transcript! Congrats! You can use the command /transcript to list your transcript at any time.")
        return HttpResponse(status=200)

    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(error_id)
        logger.error(e)
        ephemeral(client, body, f"Something went wrong! We could not record your completion. Please contact <@U01F7TAQXNG> and provide the error ID: {error_id}")

    return HttpResponse(status=200)


@csrf_exempt
@app.command("/transcript")
def transcript(ack, body, client):
    ack()
    logger.debug(body)

    results = Transcript.objects.filter(slack_user_id=body['user_id']).order_by('-time')
    output = [f"{idx} {x.channel} ({x.time})" for idx, x in enumerate(results)]

    blocks = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": random.choice(['Excellent work!', 'Way to go!', 'Great Progress!']),
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "\n".join(output),
                    "emoji": True
                }
            }
        ]
    }

    client.chat_postEphemeral(
        channel=body['channel_id'],
        user=body['user_id'],
        blocks=blocks, #f"We have recorded that you completed the following modules: {', '.join(output)}"
    )
