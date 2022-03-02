import logging
import random
import uuid
from .models import Transcript, CertificateRequest
from django.http import HttpResponse
from .videolibrary import CHANNEL_MAPPING
from django.views.decorators.csrf import csrf_exempt
import json
import os


# __import__('pprint').pprint(CHANNEL_MAPPING)
JOINED = []

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


@csrf_exempt
@app.view("view_1")
def handle_submission(ack, body, client, view, logger):
    print("Handling Submission")
    human_name = view["state"]["values"]["input_c"]["human_name"]
    print(view)
    user = body["user"]["id"]
    print(body)

    # Validate the inputs
    errors = {}
    if human_name is not None and len(human_name) < 1:
        errors["input_c"] = "You must provide a name here"

    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return

    # Acknowledge the view_submission request and close the modal
    ack()
    # Do whatever you want with the input data - here we're saving it to a DB
    # then sending the user a verification of their submission

    # Message to send user
    msg = ""
    try:
        # Save to DB
        q = CertificateRequest(slack_user_id=body['user_id'], human_name=human_name, course="GTN Tapas", approved=False)
        q.save()

        msg = f"Your request for a certificate was successful, it is pending review by a course organiser."
    except Exception as e:
        # Handle error
        error_id = str(uuid.uuid4())
        logger.error(error_id)
        logger.error(e)
        ephemeral(client, body, f"Something went wrong! Please contact <@U01F7TAQXNG> and provide the error ID: {error_id}")

    # Message the user
    try:
        ephemeral(client, body, msg)
    except e:
        error_id = str(uuid.uuid4())
        logger.error(error_id)
        logger.error(e)
        ephemeral(client, body, f"Something went wrong! Please contact <@U01F7TAQXNG> and provide the error ID: {error_id}")


@csrf_exempt
@app.command("/certify")
def certify(ack, client, body, logger, say):
    ack()
    # ephemeral(client, body, "Your request for a certificate has been received.")
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            # View identifier
            "callback_id": "view_1",
            "title": {"type": "plain_text", "text": "Certificate Name"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "input_c",
                    "label": {"type": "plain_text", "text": "Please enter your name as you would like it to appear on your certificate"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "human_name",
                        "multiline": False
                    }
                }
            ]
        }
    )


def ephemeral(client, body, message):
    client.chat_postEphemeral(
        channel=body['channel_id'],
        user=body['user_id'],
        text=message,
    )


@csrf_exempt
@app.command("/completed")
def completed(ack, body, logger, say, client):
    # Automatically try and join channels. This ... could be better.
    if body['channel_id'] not in JOINED:
        JOINED.append(body['channel_id'])
        app.client.conversations_join(channel=body['channel_id'])

    ack()
    if 'text' not in body:
        ephemeral(client, body, f":warning: Please run this command with the histories you are using as proof of completing this tutorial. E.g. /completed https://usegalaxy.../u/your-user/h/your-history\n\nWe will check these histories before granting your certificate at the end of the course.")
        return HttpResponse(status=200)

    if body['channel_name'] not in CHANNEL_MAPPING:
        ephemeral(client, body, f"This channel is not associated with a course module. If you believe this is an error, please contact <@U01F7TAQXNG>")
        return HttpResponse(status=200)

    real_module = CHANNEL_MAPPING[body['channel_name']]
    if len(real_module) == 1:
        module = real_module[0]
    else:
        module = 'channel:' + body['channel_name']

    try:
        q = Transcript(slack_user_id=body['user_id'], channel=module, proof=body['text'])
        q.save()
        ephemeral(client, body, f"Saved this course to your transcript! Congrats! You can use the command /transcript to list your transcript at any time.")
        ephemeral(client, body, f"You should write a short feedback here for the authors! Let them know how much you enjoyed the tutorial, or if you had any issues.")
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
    output = [f"{idx} {x.channel} ({x.time})" for (idx, x) in enumerate(results)]
    print(output)

    congrats = random.choice(['Excellent work!', 'Way to go!', 'Great Progress!'])
    text = f"*{congrats}*\n"
    for o in output:
        text += f"{o}\n"

    ephemeral(client, body, text)
