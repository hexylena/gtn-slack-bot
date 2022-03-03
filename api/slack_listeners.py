import logging
from django.db.models import Count
from django.db.models import DateField
from django.db.models.functions import Cast
import traceback
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
    traceback.print_exc()
    ephemeral(
        client,
        body,
        f"Something went wrong! Please contact <@U01F7TAQXNG> and provide her the error ID: {error_id}",
    )
    return HttpResponse(status=200)


def channel2module(body):
    real_module = CHANNEL_MAPPING[body["channel_name"]]
    if len(real_module) == 1:
        module = real_module[0]
    else:
        module = "channel:" + body["channel_name"]
    return module


def validateGalaxyURLs(text):
    errors = []
    if "https://" in text:
        urls = re.findall(r"https?://[^\s]+", text)
        print(f'urls: {urls}')
        if len(urls) == 0:
            errors.append(f":warning: No galaxy URLs detected.")
        for url in urls:
            try:
                resp = requests.get(url, timeout=10)
            except requests.ReadTimeout:
                errors.append(f":warning: We could not access this URL before it timed out.")
            if resp.status_code != 200:
                errors.append(f":warning: This url was not 200 OK. #{url}")
            if "galaxy" not in resp.text:
                errors.append(f":warning: This url doesn't look like a Galaxy URL. #{url}")
    else:
        errors.append(":warning: We could not find a url in your submission")
    return errors


def logReq(body):
    print(
        f"REQ | {body['user_name']} | {body['user_id']} | {body['channel_id']} | {body['channel_name']}| {body['command']} | {body.get('text', '')}"
    )


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
    if body["channel_name"] == "directmessage":
        ack(
            ":warning: This command cannot be run in a Direct Message, please run it in a channel for a tutorial."
        )
        return HttpResponse(status=200)

    # Automatically try and join channels. This ... could be better.
    if body["channel_id"] not in JOINED:
        JOINED.append(body["channel_id"])
        try:
            app.client.conversations_join(channel=body["channel_id"])
        except:
            ack(":warning: I could not automatically join this conversation, please invite me to use Certificate commands here.")
            return HttpResponse(status=200)

    ack()


    # If the body is blank (and we're not in the admin_ tutorials)
    if "text" not in body and body["channel_name"][0:6] != "admin_":
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

    module = channel2module(body)

    errors = []
    if body["channel_name"][0:6] != "admin_":
        # Then we validate URLs
        errors = validateGalaxyURLs(body.get('text', '').strip())
        if len(errors) > 0:
            msg = (
                ":warning: It seems your submission had some issues.\n\n"
                "These might be false-positives. However, if these errors look valid, then please re-run the command with /completed <your galaxy history url>\n"
                "Reminder: You can <https://training.galaxyproject.org/training-material/faqs/galaxy/histories_sharing.html|follow this tutorial> to share your history.\n"
                "\n"
            )
            for e in errors:
                msg += e + "\n"

            print(f"User submitted: {body['text']} got errors {errors} msg {msg}")
            ephemeral(client, body, msg)

    try:
        q = Transcript(
            slack_user_id=body["user_id"], channel=module, proof=body.get('text', '')
        )
        q.save()

        prompt = random.choice(
            [
                "What did you like about the material?",
                "What did you struggle with?",
                "Let us know what you thought about the material!",
            ]
        )
        msg = (
            "Saved this course to your transcript! Congrats!\n"
            "• You can use the command /transcript to list all of your completed tutorials.\n"
            "• Remember to submit a certificate request with /request-certificate before April 1st, 2022\n"
            "\n"
            ":pray: If you liked the tutorial tell the instructor thanks!\n"
            f":speaking_head_in_silhouette: {prompt}"
        )
        ephemeral(client, body, msg)

        if len(errors) == 0:
            congrats = random.choice(['Congratulations!', '¡Felicidades!', 'Fantastic work!', 'Great job!'])
            message(
                client,
                body["channel_id"],
                f"{congrats} <@{body['user_id']}> just completed this tutorial! :tada:",
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

    courses_seen = {}
    output = []
    for x in results:
        if x.channel in courses_seen:
            continue
        output.append(f"{x.time.strftime('%A, %B %d %H:%M %Z')} | {x.channel} ")
        courses_seen[x.channel] = True

    congrats = random.choice(["Excellent work!", "Way to go!", "Great Progress!"])
    text = f"*{congrats}*\n"
    for o in output:
        text += f"{o}\n"

    ephemeral(client, body, text)

@csrf_exempt
@app.command("/stats-all")
def statsall(ack, body, client):
    logReq(body)
    ack()

    results = Transcript.objects.values('channel').annotate(dcount=Count('channel')).order_by('-dcount') #.filter(dcount__gt=2)

    output = ":trophy: *Top Completed Tutorials*\n\nCount - Channel\n"
    for x in results[0:20]:
        output += f"{x['dcount']} - {x['channel']}\n"

    ephemeral(client, body, output)

@csrf_exempt
@app.command("/stats")
def stats(ack, body, client):
    logReq(body)
    ack()

    module = channel2module(body)

    results = Transcript.objects.filter(channel=module).values('time').annotate(day=Cast('time', output_field=DateField())).values('day').annotate(dcount=Count('channel')).order_by('-day')

    output = ":calendar: People Completing this tutorial by Day\n\nDay - Count\n"
    for x in results[0:20]:
        output += f"{x['channel']} - {x['dcount']}\n"

    ephemeral(client, body, output)
