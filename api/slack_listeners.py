import logging
import re
import requests
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


def ephemeral(client, body, message):
    client.chat_postEphemeral(
        channel=body["channel_id"],
        user=body["user_id"],
        text=message,
    )

def message(client, channel, message):
    client.chat_postMessage(
        channel=channel,
        text=message,
    )


def error_handler(client, body, e):
    error_id = str(uuid.uuid4())
    logger.error(error_id)
    logger.error(e)
    ephemeral(
        client,
        body,
        f"Something went wrong! Please contact <@U01F7TAQXNG> and provide them the error ID: {error_id}",
    )
    return HttpResponse(status=200)


def validateGalaxyURLs(text):
    errors = []
    if "https://" in text:
        urls = re.findall(r"https?://[^/]*/u/[^/]*/./[^ #()\[\]]*", text)
        for url in urls:
            try:
                resp = requests.get(url, timeout=10)
            except requests.ReadTimeout:
                pass

            if resp.status_code != 200:
                errors.append(f"This url was not 200 OK. #{url}")
            if "galaxy" not in resp.text:
                errors.append(f"This url doesn't look like a Galaxy URL. #{url}")
    else:
        errors.append("We could not find a url in your submission")
    return errors

def logReq(body):
    print(f"REQ | {body['user_name']} | {body['user_id']} | {body['channel_id']} | {body['channel_name']}| {body['command']} | {body.get('text', '')}")


@app.event("app_mention")
def handle_app_mentions(logger, event, say):
    logger.info(event)
    say(f"Hi there, <@{event['user']}>")


@csrf_exempt
@app.command("/request-certificate")
def certify(ack, client, body, logger, say):
    logReq(body)
    # Automatically try and join channels. This ... could be better.
    if body["channel_id"] not in JOINED:
        JOINED.append(body["channel_id"])
        app.client.conversations_join(channel=body["channel_id"])

    ack()

    if "text" not in body:
        ephemeral(
            client,
            body,
            f":warning: Please provide the name you wish to appear on your certificate, as you wish it to appear. For example: /request-certificate Jane Doe",
        )
        return HttpResponse(status=200)

    human_name = body["text"].strip()

    msg = ""
    try:
        # Save to DB
        existing_requests = CertificateRequest.objects.filter(
            slack_user_id=body["user_id"]
        )
        if len(existing_requests) == 0:
            q = CertificateRequest(
                slack_user_id=body["user_id"],
                human_name=human_name,
                course="GTN Tapas",
                approved=False,
            )
            q.save()
        else:
            existing_requests[0].human_name = human_name
            existing_requests[0].save()

        msg = f"Your request for a certificate was successful, it is pending review by a course organiser."
        ephemeral(client, body, msg)

    except Exception as e:
        # Handle error
        return error_handler(client, body, e)


@csrf_exempt
@app.command("/completed")
def completed(ack, body, logger, say, client):
    logReq(body)
    if body['channel_name'] == 'directmessage':
        ack(":warning: This command cannot be run in a Direct Message, please run it in a channel for a tutorial.")
        return HttpResponse(status=200)
    ack()

    # Automatically try and join channels. This ... could be better.
    if body["channel_id"] not in JOINED:
        JOINED.append(body["channel_id"])
        app.client.conversations_join(channel=body["channel_id"])

    if "text" not in body:
        ephemeral(
            client,
            body,
            f":warning: Please run this command with the histories you are using as proof of completing this tutorial. E.g. /completed https://usegalaxy.../u/your-user/h/your-history\n\nWe will check these histories before granting your certificate at the end of the course. You can <https://training.galaxyproject.org/training-material/faqs/galaxy/histories_sharing.html|follow this tutorial> to share your history.",
        )
        return HttpResponse(status=200)

    if body["channel_name"] not in CHANNEL_MAPPING:
        ephemeral(
            client,
            body,
            f"This channel is not associated with a course module. If you believe this is an error, please contact <@U01F7TAQXNG>",
        )
        return HttpResponse(status=200)

    real_module = CHANNEL_MAPPING[body["channel_name"]]
    if len(real_module) == 1:
        module = real_module[0]
    else:
        module = "channel:" + body["channel_name"]

    errors = []
    try:
        errors = validateGalaxyURLs(body['text'])
    except Exception as e:
        return error_handler(client, body, e)

    if errors:
        ephemeral(
            client,
            body,
            (
            ":warning: It seems your submission had some issues.\n\n"
            "These might be false-positives. However, if these errors look valid, then please re-run the command with /completed <your galaxy history url>\n"
            "Reminder: You can <https://training.galaxyproject.org/training-material/faqs/galaxy/histories_sharing.html|follow this tutorial> to share your history.\n"
            "\n"
            "\n".join(errors)
            )
        )
        print(f"User submitted: {body['text']}")

    try:
        q = Transcript(
            slack_user_id=body["user_id"], channel=module, proof=body["text"]
        )
        q.save()

        message(client, body['channel_id'], "Congratulations <@{body['user_id']}> on completing this tutorial! :tada:")
        ephemeral(
            client,
            body,
            (
                "Saved this course to your transcript! Congrats!\n"
                "• You can use the command /transcript to list your transcript at any time.\n"
                "• Remember to submit a certificate request with /request-certificate before April 1st, 2022\n"
                "\n"
                ":pray: If you liked the tutorial tell the instructor thanks!\n"
                ":speaking_head_in_silhouette: " + random.choice(['What did you like about the material?', 'What did you struggle with?', 'Let us know what you thought about the material!']),
            )
        )
        return HttpResponse(status=200)

    except Exception as e:
        return error_handler(client, body, e)

    return HttpResponse(status=200)


@csrf_exempt
@app.command("/transcript")
def transcript(ack, body, client):
    logReq(body)
    ack()
    logger.debug(body)

    results = Transcript.objects.filter(slack_user_id=body["user_id"]).order_by("-time")
    output = [
        f"{x.channel:<30} ({x.time.strftime('%A, %B %d')})"
        for (idx, x) in enumerate(results)
    ]
    print(output)

    congrats = random.choice(["Excellent work!", "Way to go!", "Great Progress!"])
    text = f"*{congrats}*\n"
    for o in output:
        text += f"{o}\n"

    ephemeral(client, body, text)
