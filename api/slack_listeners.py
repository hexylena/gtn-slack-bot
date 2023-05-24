import logging
from django.db.models import Count
from django.db.models import DateField
from django.db.models.functions import Cast
import time
import datetime
import traceback
import re
import requests
import random
import uuid

from .models import Transcript, CertificateRequest
from django.http import HttpResponse
from .videolibrary import CHANNEL_MAPPING, channel2module, validateGalaxyURLs, addCertificateRequest
from django.views.decorators.csrf import csrf_exempt
from .i18n import ENCOURAGEMENT
import json

logger = logging.getLogger(__name__)
from .slack import app
import os

TRANSCRIPT_ENCOURAGEMENT = ["Excellent work!", "Way to go!", "Great Progress!"]
START_TIME = time.time()
JOINED = []

# conversations = app.client.conversations_list(limit=400).data
# for convo in conversations:
#    if convo['is_member'] is True:
#        JOINED.append(convo['name'])



# I'm alive
# Disabled because of cron jobs
#try:
#    result = app.client.chat_postMessage(
#        channel="C01PQ3P2TTL",
#        text="I'm alive"
#    )
#except Exception as e:
#    print(f"Error: {e}")


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
    ephemeral(
        client,
        body,
        f"Something went wrong! Please contact <@U01F7TAQXNG> and provide her the error ID: {error_id}",
    )
    return HttpResponse(status=200)


def logReq(body):
    print(
        f"REQ | {body['user_name']} | {body['user_id']} | {body['channel_id']} | {body['channel_name']}| {body['command']} | {body.get('text', '')}"
    )


def auto_join_channel(body, ack):
    # Automatically try and join channels. This ... could be better.
    if body["channel_id"] not in JOINED:
        JOINED.append(body["channel_id"])
        try:
            app.client.conversations_join(channel=body["channel_id"])
        except:
            ack(
                ":warning: I could not automatically join this conversation, please invite me to use Certificate commands here."
            )
            return HttpResponse(status=200)


USER_PROFILE_CACHE = {}
def get_user_info_cached(user_id):
    if user_id not in USER_PROFILE_CACHE:
        info = app.client.users_info(user=user_id)
        USER_PROFILE_CACHE[user_id] = info
    return USER_PROFILE_CACHE[user_id]


def easter_egg(client, body):
    info = get_user_info_cached(body['user_id'])
    emoji = info['user']['profile']['status_emoji']
    if emoji == ':transgender_flag:':
        ephemeral(client, body, ":rainbow-flag: Thanks for advancing the trans agenda by taking over science! :test_tube::transgender_flag: (this message appears to you due to your chosen Slack status emoji.)")
    elif emoji == ':rainbow-flag':
        ephemeral(client, body, ":rainbow-flag: Thanks for advancing the queer agenda by taking over science! :microscope::rainbow-flag: (this message appears to you due to your chosen Slack status emoji.)")


@csrf_exempt
@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    try:
        # views.publish is the method that your app uses to push a view to the Home tab
        client.views_publish(
            # the user that opened your app's app home
            user_id=event["user"],
            # the view object that appears in the app home
            view={
                "type": "home",
                "callback_id": "home_view",

                # body of the view
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Welcome to the _GTN Certificate Bot_* :tada:"
                        }
                    },
                    {
                        "type": "divider"
                    },
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@csrf_exempt
@app.message(re.compile(".*"))
def handle_messages2(message, say, logger):
    print('messages2', event)
    logger.info(event)

@csrf_exempt
@app.event("message")
def handle_messages(event, logger):
    print('messages', event)
    logger.info(event)


@csrf_exempt
@app.event("reaction_added")
def handle_reactions(event, logger):
    print(event)
    logger.info(event)


@csrf_exempt
@app.event("app_mention")
def handle_app_mentions(logger, event, say):
    logger.info(event)
    say(f"Hi there, <@{event['user']}>\n\n<https://gallantries.github.io/video-library/certbot|Were you trying to submit a certificate?> You must put /certificate at the start of your message. Please try again!")


@csrf_exempt
@app.command("/info")
def certify(ack, client, body, logger, say):
    ack()

    r = requests.get('https://ipinfo.io/json').json()
    org = r['org']
    ip = r['ip']

    if 'GIT_REV' in os.environ:
        url = f"https://github.com/hexylena/gtn-slack-bot/commit/{os.environ['GIT_REV']}"
    else:
        url = "https://github.com/hexylena/gtn-slack-bot/"

    data = {
        ':classical_building: Org': org,
        ':computer: IP': ip,
        ':robot_face: Deployment': url,
        ':clock330: Execution Time': datetime.timedelta(seconds=time.process_time()),
        ':alarm_clock: Uptime': datetime.timedelta(seconds=time.time() - START_TIME),
    }

    fmt_msg = "\n".join([f"{k}: {v}" for (k, v) in data.items()])

    ephemeral(
        client,
        body,
        fmt_msg,
    )


@csrf_exempt
@app.command("/request-certificate")
def certify(ack, client, body, logger, say):
    logReq(body)
    auto_join_channel(body, ack)
    if '://' in body['text']:
        ack(":octagonal_sign: Human names do not contain URLs, please retry.")
        return HttpResponse(status=200)

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
        addCertificateRequest(body['user_id'], human_name)
        ephemeral(client, body, f"Your request for a certificate was successful, it is pending review by a course organiser. Your name will appear as '{human_name}' on your certificate (exactly as it appears between the 'single quotes'.) If you need to correct this, just re-run the command with your corrected name.")
    except Exception as e:
        # Handle error
        return error_handler(client, body, e)

    ephemeral(
        client,
        body,
        f":warning: As a final requirement for your certificate, please fill in the feedback <https://docs.google.com/forms/d/e/1FAIpQLSeZ6hCdXNsurYs6Oa9AWoAf4ifwzQK_FAY4RQ8TomnlqJW9Kg/viewform?usp=sf_link|via our feedback survey>, if you have not done so already!",
    )


@csrf_exempt
@app.command("/completed")
def completed(ack, body, logger, say, client):
    logReq(body)
    #ack(
    #    ":octagonal_sign: This event is unfortunately over. Check back next year for Smörgåsbord 3!"
    #)
    #return HttpResponse(status=200)

    if body["channel_name"] == "directmessage":
        ack(
            ":warning: This command cannot be run in a Direct Message, please run it in a channel for a tutorial."
        )
        return HttpResponse(status=200)
    auto_join_channel(body, ack)
    ack()

    # If the body is blank (and we're not in the admin_ tutorials)
    if "text" not in body and body["channel_name"][0:6] != "admin_":
        ephemeral(
            client,
            body,
            f":warning: Please run this command with the histories you are using as proof of completing this tutorial. E.g. /completed https://usegalaxy.../u/your-user/h/your-history\n\nWe will check these histories before granting your certificate at the end of the course. You can <https://training.galaxyproject.org/training-material/faqs/galaxy/histories_sharing.html|follow this tutorial> to share your history.",
        )
        return HttpResponse(status=200)

    #if body["channel_name"] not in CHANNEL_MAPPING:
        # This is potentially a self-study or other weird one.
        #ephemeral(
        #    client,
        #    body,
        #    f"This channel is not associated with a course module. If you believe this is an error, please contact <@U01F7TAQXNG>",
        #)
        #return HttpResponse(status=200)

    module = channel2module(body)

    errors = []
    fatalities = []
    if body["channel_name"][0:6] != "admin_" and body["channel_name"][0:4] != "dev_":

        # Then we validate URLs
        (errors, fatalities) = validateGalaxyURLs(body.get("text", "").strip())
        if len(fatalities) > 0:
            msg = ":octagonal_sign: Your submission had some issues. We believe it may not contain a Galaxy History URL\n\n"
            for e in fatalities:
                msg += e + "\n"

            msg += (
                "Galaxy history URLs look like https://usegalaxy.xx/u/saskia/h/my-history-name.\n"
                "Need to know how to share your history? <https://training.galaxyproject.org/training-material/faqs/galaxy/histories_sharing.html|Follow this tutorial!>\n"
                "\n"
                "This _might_ be a false-positive. If you believe the URL you're trying to submit is correct, please contact <@U01F7TAQXNG> and provide her with the following information:\n"
                f"> Channel: {body['channel_name']}\n"
                f"> URL: {body.get('text', 'No text submitted')}"
            )
            print(
                f"User submitted: {body['text']} got fatalities {fatalities} msg {msg}"
            )
            ephemeral(client, body, msg)
            return HttpResponse(status=200)
        elif len(errors) > 0:
            msg = (
                ":warning: It seems your submission had some issues.\n\n"
                "These _might_ be false-positives. However, if these errors look valid, then please re-run the command with /completed <your galaxy history url>\n"
                "Reminder: You can <https://training.galaxyproject.org/training-material/faqs/galaxy/histories_sharing.html|follow this tutorial> to share your history.\n"
                "\n"
            )
            for e in errors:
                msg += e + "\n"

            print(f"User submitted: {body['text']} got errors {errors} msg {msg}")
            ephemeral(client, body, msg)

    try:
        easter_egg(client, body)
    except Exception as e:
        print(f"XXX {e}")
        pass

    try:
        q = Transcript(
            slack_user_id=body["user_id"], channel=module, proof=body.get("text", "")
        )
        q.save()
        # Ensure everyone has an automatic certificate request.
        addCertificateRequest(body['user_id'], body['user_id'])

        prompt = random.choice(
            [
                "What did you like about the material?",
                "What did you struggle with?",
                "Let us know what you thought about the material!",
            ]
        )
        msg = (
            f"You submitted proof for *{module}* in <#{body['channel_id']}>. Congrats!\n"
            "• Did you mean to register completion of another tutorial? That's fine, go do it in that channel!\n"
            "• You can use the command /transcript to list all of your completed tutorials.\n"
            "• Remember to submit a certificate request with /request-certificate before April 1st, 2022\n"
            "\n"
            ":pray: If you liked the tutorial tell the instructor thanks! Write a message in this channel!\n"
            f":speaking_head_in_silhouette: {prompt} Write it here and let us know!"
        )
        ephemeral(client, body, msg)

        if len(errors) == 0:
            congrats = random.choice(ENCOURAGEMENT)
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
    auto_join_channel(body, ack)
    ack()

    results = Transcript.objects.filter(slack_user_id=body["user_id"]).order_by("-time")

    courses_seen = {}
    output = []
    for x in results:
        if x.channel in courses_seen:
            continue
        output.append(f"{x.time.strftime('%A, %B %d %H:%M %Z')} | {x.channel} ")
        courses_seen[x.channel] = True

    congrats = random.choice(TRANSCRIPT_ENCOURAGEMENT)
    text = f"*{congrats}*\n"
    for o in output:
        text += f"{o}\n"

    ephemeral(client, body, text)


@csrf_exempt
@app.command("/stats-all")
def statsall(ack, body, client):
    logReq(body)
    auto_join_channel(body, ack)
    ack()

    if 'text' in body and len(body['text'].strip()) > 0:
        results = Transcript.objects.filter(channel__icontains=body['text'].lower()).values('channel').annotate(Count('slack_user_id', distinct=True)).order_by('-slack_user_id__count')
    else:
        results = Transcript.objects.values('channel').annotate(Count('slack_user_id', distinct=True)).order_by('-slack_user_id__count')

    output = ":trophy: *Top Completed Tutorials*\n\nCount - Channel\n"
    for x in results[0:20]:
        output += f"{x['slack_user_id__count']} - {x['channel']}\n"

    ephemeral(client, body, output)


@csrf_exempt
@app.command("/stats")
def stats(ack, body, client):
    logReq(body)
    if body["channel_name"] == "directmessage":
        ack(
            ":warning: This command cannot be run in a Direct Message, please run it in a channel for a tutorial."
        )
        return HttpResponse(status=200)
    auto_join_channel(body, ack)
    ack()

    module = channel2module(body)

    results = Transcript.objects.filter(channel=module).values('time', 'slack_user_id').annotate(day=Cast("time", output_field=DateField())).values('day').annotate(Count('slack_user_id', distinct=True)).order_by("-day")
    # results = (
        # Transcript.objects.filter(channel=module)
        # .values("time")
        # .annotate(day=Cast("time", output_field=DateField()))
        # .values("day")
        # .annotate(dcount=Count("day"))
        # .order_by("-day")
    # )

    output = ":calendar: People completing this tutorial by Day\n\nDay - Count\n"
    for x in results[0:20]:
        output += f"{x['day']} - {x['slack_user_id__count']}\n"

    ephemeral(client, body, output)
