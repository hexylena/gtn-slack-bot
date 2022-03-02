import logging
from .models import Transcript
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os

file_path = os.path.dirname(os.path.abspath(__file__))
videosjson = os.path.join(file_path, 'videos.json')
with open(videosjson, 'r') as handle:
    videos = json.load(handle)

def convert_name(path):
    path_parts = path.split('/')
    if path_parts[0] == 'statistics':
        path_parts[0] = 'machine_learning'
    if path_parts[0] == 'sequence-analysis':
        path_parts[0] = 'ngs'

    if 'galaxy/intro' in path or path_parts[0] == 'introduction':
        return 'galaxy-intro'
    elif path_parts[0] in ('galaxy', 'community', 'webinar'):
        return 'general'
    elif path_parts[0] == 'course':
        # These are specific to their events
        return '-'.join(['event', path_parts[1].replace('welcome-', '')])
    elif path_parts[0] == 'contributing':
        return 'gtn'
    elif 'tool-generators' in path_parts[1]:
        return 'dev-toolfactory'
    elif len(path_parts) > 2 and path_parts[2] in ('tutorial', 'slides'):
        return "_".join(path_parts[0:2])
    elif len(path_parts) > 2:
        return "_".join(path_parts[0:2])
    elif len(path_parts) == 2:
        return "_".join(path_parts[0:2])
    return None

channel_mapping = {}
for k, v in videos.items():
    c = convert_name(k)
    if c not in channel_mapping:
        channel_mapping[c] = []

    channel_mapping[c].append(k)

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
@app.command("/completed")
def completed(ack, body, logger, say, client):
    ack()
    if 'text' not in body:
        client.chat_postEphemeral(
            channel=body['channel_id'],
            user=body['user_id'],
            text=f":warning: Please run this command with the histories you are using as proof of completing this tutorial. E.g. /completed https://usegalaxy.../u/your-user/h/your-history\n\nWe will check these histories before granting your certificate at the end of the course.",
        )
        return HttpResponse(status=200)

    if body['channel_name'] not in channel_mapping:
        client.chat_postEphemeral(
            channel=body['channel_id'],
            user=body['user_id'],
            text=f"This channel is not associated with a course module. If you believe this is an error, please contact <@U01F7TAQXNG>"
        )
        return HttpResponse(status=200)

    real_module = channel_mapping[body['channel_name']]
    if len(real_module) == 1:
        module = real_module[1]
    else:
        print(f'qq {real_module}')
        logging.warning(f'zz {real_module}')

    try:
        q = Transcript(slack_user_id=body['user_id'], channel=module, proof=body['text'])
        q.save()
        client.chat_postEphemeral(
            channel=body['channel_id'],
            user=body['user_id'],
            text=f"Saved this course to your transcript! Congrats! You can use the command /transcript to list your transcript at any time."
        )
        return HttpResponse(status=200)

    except Exception as e:
        logger.error(e)
        client.chat_postEphemeral(
            channel=body['channel_id'],
            user=body['user_id'],
            text=f"Something went wrong! ({e}) We could not record your completion. Please contact <@U01F7TAQXNG>"
        )

    return HttpResponse(status=200)


@csrf_exempt
@app.command("/transcript")
def transcript(ack, body, client):
    ack()
    logger.debug(body)

    results = Transcript.objects.filter(slack_user_id=body['user_id'])
    output = [x.channel for x in results]

    # say(
        # text=",
        # ephemeral=True
    # )
    client.chat_postEphemeral(
        channel=body['channel_id'],
        user=body['user_id'],
        text=f"We have recorded you completed the following modules: {', '.join(output)}"
    )
