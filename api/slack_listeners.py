import logging
from django.utils import timezone
from django.db.models import Count
from django.db.models import DateField
from django.db.models.functions import Cast
import os
import time
import datetime
import traceback
import re
import requests
import random
import uuid

from .models import Transcript, CertificateRequest, Gratitude
from django.http import HttpResponse
from .videolibrary import CHANNEL_MAPPING, channel2module, validateGalaxyURLs, addCertificateRequest, CHANNEL_GROUPS, BAD_COMPLETED
from django.views.decorators.csrf import csrf_exempt
from .i18n import ENCOURAGEMENT
import json

logger = logging.getLogger(__name__)
from .slack import app
import os

ENABLED = False
TRANSCRIPT_ENCOURAGEMENT = ["Excellent work!", "Way to go!", "Great Progress!"]
START_TIME = time.time()
JOINED = []

# conversations = app.client.conversations_list(limit=400).data
# for convo in conversations:
#    if convo['is_member'] is True:
#        JOINED.append(convo['name'])


# TODO: add tags for message type (channel, direct, etc), channel, user?
# https://docs.sentry.io/platforms/python/enriching-events/tags/


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


def get_transcript_mkrdwn(slack_user_id):
    results = Transcript.objects.filter(slack_user_id=slack_user_id).order_by("-time")

    courses_seen = {}
    output = []
    dates = {}
    for x in results:
        if x.channel in courses_seen:
            continue
        day = x.time.strftime('%B %d, %A')
        if day not in dates:
            dates[day] = []

        dates[day].append(f"{x.time.strftime('%H:%M %Z')} | {x.channel} ")
        courses_seen[x.channel] = True

    congrats = random.choice(TRANSCRIPT_ENCOURAGEMENT)
    text = f"*{congrats}*\n"
    for d in sorted(dates.keys()):
        text += f"\n*{d}*\n\n"
        for o in dates[d]:
            text += f"{o}\n"
    return text


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    text = get_transcript_mkrdwn(event['user'])

    home = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Welcome to the GTN Certificate Bot :gtn:",
                "emoji": True
            }
        },
        {
            "type": "divider"
        },
    ]

    certificate_request = addCertificateRequest(app, event['user'])

    # For students, their transcript
    home.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "Certificate Status :scroll:",
            "emoji": True
        }
    })
    home.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Name on Certificate: *{certificate_request.human_name}*"
        }
    })

    CertificateStates = {
        'ACC': 'Accepted',
        'REJ': 'Rejected (No valid transcripts found)',
        'UNK': 'Unknown',
        'S/S': 'Certificate Sent',
        'R/S': 'Rejection Sent',
    }
    home.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Certificate Status: {CertificateStates[certificate_request.approved]}"
        }
    })
    home.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "Transcript :galaxy:",
            "emoji": True
        }
    })
    home.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Here is your current *transcript*:\n\n" + text
        }
    })
    client.views_publish(
        # the user that opened your app's app home
        user_id=event["user"],
        view={
            "type": "home",
            "callback_id": "home_view",
            "blocks": home
        }
    )


@app.event("message")
def handle_messages(event, logger, client):
    print('messages', event)
    # {'client_msg_id': '816539f7-a2af-4737-8c46-f8fa65c50064', 'type': 'message', 'text': 'Thanks Saskia for your reply, I will try this tools', 'user': 'U059H56UFFA', 'ts': '1685436611.427609', 'blocks': [{'type': 'rich_text', 'block_id': 'XsLx', 'elements': [{'type': 'rich_text_section', 'elements': [{'type': 'text', 'text': 'Thanks Saskia for your reply, I will try this tools'}]}]}], 'team': 'T01EL3YJPC2', 'thread_ts': '1685435549.297769', 'parent_user_id': 'U059H56UFFA', 'channel': 'C01FQ92MB7A', 'event_ts': '1685436611.427609', 'channel_type': 'channel'}

    # Ignore messages in threads
    if 'thread_ts' in event:
        return

    if 'text' not in event:
        print("Missing text field")
        return

    if BAD_COMPLETED.match(event['text']):
        message(
            client,
    # Only in channels
            event["channel"],
            f"Hey <@{event['user']}>, it looks like you're trying to use the completed command. This didn't quite work, so please try again with /completed at the *start* of your message, nothing before it. See https://gallantries.github.io/video-library/certbot for more details including a video!",
        )



SEEN_GRATITUDE = {}
SEEN_SUPPORT_AU = {}
SEEN_SUPPORT_US = {}
SEEN_SUPPORT_EU = {}

@app.event("reaction_added")
def handle_reactions(client, event, logger):
    #{'type': 'reaction_added', 'user': 'U058SE9GY8P', 'reaction': 'yellow_heart', 'item': {'type': 'message', 'channel': 'C01ES8R0RNG', 'ts': '1684920076.690419'}, 'item_user': 'U01EDBVM04W', 'event_ts': '1684926148.066100'}
    key = event['item']['channel'] + event['item']['ts']
    url = f"https://gtnsmrgsbord.slack.com/archives/{event['item']['channel']}/p{event['item']['ts'].replace('.', '')}"

    if 'gtn-support-' in event['reaction']:
        logger.info(event)

        if event['reaction'] == 'gtn-support-au':
            if key in SEEN_SUPPORT_AU:
                return
            message(
                client,
                "#support-au",
                url
            )
            SEEN_SUPPORT_AU[key] = True
        elif event['reaction'] == 'gtn-support-us':
            if key in SEEN_SUPPORT_US:
                return
            message(
                client,
                "#support-us",
                url
            )
            SEEN_SUPPORT_US[key] = True
        elif event['reaction'] == 'gtn-support-eu':
            if key in SEEN_SUPPORT_EU:
                return
            message(
                client,
                "#support-eu",
                url
            )
            SEEN_SUPPORT_EU[key] = True
        return

    if 'gratitude-' in event['reaction']:
        if key in SEEN_GRATITUDE:
            return

        logger.info(event)
        message(
            client,
            "#gratitude",
            url
        )

        SEEN_GRATITUDE[key] = True

        discovered_messages = client.conversations_history(
            channel=event['item']['channel'],
            inclusive=True,
            oldest=event['item']['ts'],
            limit=1
        )

        message_text = discovered_messages['messages'][0]['text']

        Gratitude.objects.create(
            slack_channel_id=event['item']['channel'],
            date=datetime.datetime.utcfromtimestamp(int(float(event['item']['ts']))),
            message=message_text
        )



@app.event("app_mention")
def handle_app_mentions(logger, event, say):
    logger.info(event)
    say(f"Hi there, <@{event['user']}>\n\n<https://gallantries.github.io/video-library/certbot|Were you trying to submit a certificate?> You must put /certificate at the start of your message. Please try again!")


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

@app.command("/bulk-join")
def bulk_join(ack, client, body, logger, say):
    ack()

    header = False
    for groups in batch(sorted(CHANNEL_GROUPS), n=5):

        blocks = []
        # For instructors, add a series of buttons
        actions = {
            "type": "actions",
            #"fallback": "You are unable to choose a channel",
            #"callback_id": "join_channel_auto",
            "elements": [ ]
        }
        for group in groups:
            actions['elements'].append({
                'type': 'button',
                'text': {
                    'type': 'plain_text',
                    'text': group,
                    'emoji': True,
                },
                'value': f'{group}',
                'action_id': f'join_action_{group}'
            })

        if header is False:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Join groups of channels by clicking these buttons"
                }
            })
            header = True

        blocks.append(actions)
        import json
        print(json.dumps(blocks))

        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=body["user_id"],
            text="Select channels to join",
            blocks=blocks
        )

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

    human_name = body["text"].strip()#.lstrip('*').rstrip('*').lstrip('[').rstrip(']')
    if re.match(r'\*.*\*', human_name):
        human_name = human_name.lstrip('*').rstrip('*')
    if re.match(r'\[.*\]', human_name):
        human_name = human_name.lstrip('[').rstrip(']')
    if re.match(r"'.*'", human_name):
        human_name = human_name.lstrip("'").rstrip("'")

    msg = ""
    try:
        cr = addCertificateRequest(app, body['user_id'])
        cr.human_name = human_name
        cr.human_name_updated = timezone.now()
        cr.save()
        ephemeral(client, body, f"Your request for a certificate was successful, it is pending review by a course organiser. Your name will appear as '{human_name}' on your certificate (exactly as it appears between the 'single quotes'.) If you need to correct this, just re-run the command with your corrected name.")
    except Exception as e:
        # Handle error
        return error_handler(client, body, e)

    ephemeral(
        client,
        body,
        f":warning: As a final requirement for your certificate, please fill in the feedback <https://docs.google.com/forms/d/e/1FAIpQLSdth4MopsMalwye3jMl1xUhL-P-ZPOC6QYnzbDAxEhTTi1QkA/viewform?usp=sf_link|via our feedback survey>, if you have not done so already!",
    )


@app.command("/completed")
def completed(ack, body, logger, say, client):
    logReq(body)
    if not ENABLED:
        ack(
           ":octagonal_sign: This event is unfortunately over. Check back next year for Smörgåsbord 4?"
        )
        return HttpResponse(status=200)

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
        addCertificateRequest(app, body['user_id'])

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
            "• Remember to submit a certificate request with /request-certificate before June 4, 2023\n"
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


@app.command("/transcript")
def transcript(ack, body, client):
    logReq(body)
    auto_join_channel(body, ack)
    ack()

    text = get_transcript_mkrdwn(body["user_id"])
    ephemeral(client, body, text)


@app.command("/stats-all")
def statsall(ack, body, client):
    logReq(body)
    auto_join_channel(body, ack)
    ack()

    if 'text' in body and len(body['text'].strip()) > 0:
        results = Transcript.objects.filter(channel__icontains=body['text'].lower()).values('channel').annotate(Count('slack_user_id', distinct=True)).order_by('-slack_user_id__count')
    else:
        results = Transcript.objects.values('channel').annotate(Count('slack_user_id', distinct=True)).order_by('-slack_user_id__count')

    # Count total transcripts
    total_users = CertificateRequest.objects.all().count()
    total_transcripts = Transcript.objects.all().count()

    output = f":gtn-heart: *{total_users} trainees* have together completed *{total_transcripts} tutorials* :galaxy:\n\n"
    output += ":trophy: *Top Completed Tutorials*\n\nCount - Channel\n"
    for x in results[0:20]:
        output += f"{x['slack_user_id__count']} - {x['channel']}\n"

    ephemeral(client, body, output)


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
