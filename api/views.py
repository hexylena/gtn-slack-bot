import json
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
import pytz
from csp.decorators import csp_exempt
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from api.forms import ScheduleMessageForm, ScheduleMessageSingleForm
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import loader
import bleach
from api.models import Transcript, CertificateRequest, ScheduledMessage, Gratitude, Event, EventOrganiser
from django.http import JsonResponse
from api.videolibrary import CHANNEL_MAPPING, get_transcript_mkrdwn
from slack_bolt import App
from django.views.decorators.csrf import csrf_exempt
import os
import logging

logger = logging.getLogger(__name__)
from .slack import app
from .build import template_messages


def _list_channels():
    print("Listing Chanenls")
    channels = []
    cid = None
    while True:
        try:
            r = app.client.conversations_list(limit=500, cursor=cid)
            channels += r.data["channels"]
            cid = r.data["response_metadata"]["next_cursor"]
            if cid == "" or cid is None:
                break

        except KeyError:
            break
    return channels

def probably_hist(text):
    return '/u/' in text and ('/h/' in text or '/w/' in text)


def template(name, request, context=None):
    if context is None:
        context = {}

    template = loader.get_template(name)
    context.update({
        'GIT_REVISION': settings.GIT_REVISION,
    })
    return HttpResponse(template.render(context, request))


def index(request):
    return template('index.html', request)


global CACHED_CHANNELS
CACHED_CHANNELS = None # _list_channels()

def gratitude_list(request):
    global CACHED_CHANNELS
    if CACHED_CHANNELS is None:
        CACHED_CHANNELS = _list_channels()

    trans = Gratitude.objects.all().order_by('slack_channel_id')
    # {'id': 'C059LBKSNQY', 'name': 'single-cell_bulk-music-4-compare', 'is_channel': True, 'is_group': False, 'is_im': False, 'is_mpim': False, 'is_private': False, 'created': 1684768720, 'is_archived': False, 'is_general': False, 'unlinked': 0, 'name_normalized': 'single-cell_bulk-music-4-compare', 'is_shared': False, 'is_org_shared': False, 'is_pending_ext_shared': False, 'pending_shared': [], 'context_team_id': 'T01EL3YJPC2', 'updated': 1684768720150, 'parent_conversation': None, 'creator': 'U01MM8XBJ7R', 'is_ext_shared': False, 'shared_team_ids': ['T01EL3YJPC2'], 'pending_connected_team_ids': [], 'is_member': True, 'topic': {'value': '', 'creator': '', 'last_set': 0}, 'purpose': {'value': '', 'creator': '', 'last_set': 0}, 'previous_names': [], 'num_members': 10}]
    channels = {
        x['id']: x
        for x in CACHED_CHANNELS
    }
    distinct_channels = Gratitude.objects.order_by().values_list('slack_channel_id', flat=True).distinct()
    distinct_channels = [(x, channels[x]['name']) for x in distinct_channels]
    #import pprint; pprint.pprint(distinct_channels)
    context = {
        'messages': trans,
        'channels': channels,
        'distinct': distinct_channels,
    }
    return template('gratitude_list.html', request, context)


@login_required
def transcript_list(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    trans = CertificateRequest.objects.filter(event=event).order_by('slack_user_id')
    done = 0
    if len(trans) > 0:
        done = 100 * len([x.state for x in trans if x.state != 'UNK']) / len(trans)
    context = {
        'event': event,
        'users': trans,
        'done': done
    }
    return template('transcript_list.html', request, context)


@csrf_exempt
def send_message_to_channel(request, channel_id):
    if channel_id != 'C01PQ3P2TTL':
        return HttpResponse("Testing only.", status=403)

    if request.method != 'POST':
        return

    blocks = json.loads(request.body)
    try:
        app.client.conversations_join(channel=channel_id)
    except:
        return HttpResponse("Could not join conversation", status=500)

    app.client.chat_postMessage(
        channel=channel_id,
        blocks=blocks
    )
    return HttpResponse("Done")

JOINED = []

@csrf_exempt
def slack_button(request):
    body = request.body

    if request.method != 'POST':
        return

    data = json.loads(request.POST['payload'])
    user = data['user']['id']

    if data['callback_id'] == 'admin_activate_transcript':
        # {'type': 'message_action', 'token': '', 'action_ts': '1686752778.566596', 'team': {'id': 'T01EL3YJPC2', 'domain': 'gtnsmrgsbord'}, 'user': {'id': 'U01F7TAQXNG', 'username': 'helena.rasche', 'team_id': 'T01EL3YJPC2', 'name': 'helena.rasche'}, 'channel': {'id': 'C01PQ3P2TTL', 'name': 'testing'}, 'is_enterprise_install': False, 'enterprise': None, 'callback_id': 'admin_activate_transcript', 'trigger_id': '############################################################', 'response_url': 'https://hooks.slack.com/app/##################################################', 'message_ts': '1685438052.975119', 
        # 'message': {'client_msg_id': '2a3f23df-82ba-4d0e-8fef-464f121dbe9c',
        #             'type': 'message', 'text': '/<https://usegalaxy.eu/u/nziparfait/h/smorgasbordnzi2023|completed>',
        #             'user': 'U01F7TAQXNG', 'ts': '1685438052.975119', 'blocks': [], 'team': 'T01EL3YJPC2', 'attachments': []}}
        ALLOWED_USERS = ['U01F7TAQXNG']
        # TODO: check admin status
        if data['user']['id'] not in ALLOWED_USERS:
            raise PermissionDenied()

        target_slack_user_id = data['message']['user']
        transcript = get_transcript_mkrdwn(target_slack_user_id)
        print(data)
        print(transcript)

        # TODO:
        # pop a modal with their transctipt.
        view = {
          "trigger_id": data['trigger_id'],
          "view": {
            "type": "modal",
            "callback_id": "edit-task",
            "title": {
              "type": "plain_text",
              "text": "Edit task details"
            },
            "submit": {
                "type": "plain_text",
                "text": "Create"
            },
            "blocks": [
              {
                "type": "input",
                "block_id": "edit-task-title",
                "label": {
                  "type": "plain_text",
                  "text": "Task title"
                },
                "element": {
                  "type": "plain_text_input",
                  "action_id": "task-title-value",
                  "initial_value": "Block Kit documentation"
                },
              },
              {
                "type": "input",
                "block_id": "edit-ticket-desc",
                "label": {
                  "type": "plain_text",
                  "text": "Ticket description"
                },
                "element": {
                  "type": "plain_text_input",
                  "multiline": True,
                  "action_id": "ticket-desc-value",
                  "initial_value": "Update Block Kit documentation to include Block Kit in new surface areas (like modals)."
                }
              }
            ]
          }
        }
        #app.views.open(view=view)
    else:
        # Channel joining
        channel_group = data['actions'][0]['value']

        # Load channel data if not already present
        global CACHED_CHANNELS
        if CACHED_CHANNELS is None:
            CACHED_CHANNELS = _list_channels()
        channels = {
            x['id']: x
            for x in CACHED_CHANNELS
            if x['is_archived'] is False
            and x['is_channel'] is True
        }
        import pprint; pprint.pprint(channels)

        # Find channels for this group
        print(channel_group)
        print(channels.keys())
        should_join = [x for x in channels.keys() if channels[x]['name'].startswith(channel_group)]

        print(f"Inviting {user} ({data['user']['name']}) to {len(should_join)} channels: {should_join}")
        for channel in should_join:
            print(f"Channel {channels[channel]['name']}")
            # Make sure we're in this channel first
            if channel not in JOINED:
                JOINED.append(channel)
                try:
                    app.client.conversations_join(channel=channel)
                except:
                    print(f"Could not join conversation {channel}")
            # Add user to channel
            try:
                app.client.conversations_invite(
                    channel=channel, users=user
                )
            except:
                print(f"Could not invite {user} to {channel}")
    return HttpResponse("Done")


@login_required
def schedule_message_single(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        print("RECV SCHEDULE SINGLE")
        # create a form instance and populate it with data from the request:
        form = ScheduleMessageSingleForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            print("VALID FORM")
            ScheduledMessage.objects.create(**form.cleaned_data)
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect("/schedule-single/")

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ScheduleMessageSingleForm(initial={"scheduled_for": timezone.now()})

    messages = ScheduledMessage.objects.all()
    return render(request, "schedule.html", {"form": form, "type": "Single", "action": "schedule-single", "messages": messages})


@login_required
def schedule_message(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        print("RECV SCHEDULE")
        # create a form instance and populate it with data from the request:
        form = ScheduleMessageForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            print("VALID FORM")
            options = form.cleaned_data
            options['start'] = options['start'].astimezone().replace(tzinfo=None)
            template_messages(
                    zones=['Pacific/Auckland', 'Europe/Amsterdam', 'America/New_York'],
                    dry_run=False,
                    **options)
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect("/schedule")

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ScheduleMessageForm(initial={"start": timezone.now()})

    messages = ScheduledMessage.objects.all()
    return render(request, "schedule.html", {"form": form, "type": "Batch", "action": "schedule", "messages": messages})


@login_required
def dump_tsv(request):
    x = Transcript.objects.filter(valid=True).values_list('slack_user_id', 'time', 'channel')
    res = "\n".join([
        '\t'.join([row[0], row[1].strftime('%Y-%m-%d %H:%M:%S.%f%z'), row[2]])
        for row in x
    ])
    return HttpResponse(res, content_type='text/tsv')


@login_required
def event_list(request):
    events = request.user.eventorganiser.events.all()
    return template('eventlist.html', request, {'events': events, 'user': request.user})


@login_required
def event_home(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return template('event.html', request, {'event': event, 'user': request.user})

@login_required
def transcript(request, event_id, slack_user_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        results = {}
        for k, v in request.POST.items():
            if not (k.startswith('valid') or k.startswith("actual_course")):
                continue

            # Parse out the identifiers
            type, cid = k.split('.')
            cid = int(cid)

            if cid not in results:
                results[cid] = {}

            if type == 'valid':
                results[cid]['valid'] = True
            elif type == 'actual_course':
                results[cid]['course'] = v

        results_valid = {k: v for k, v in results.items() if v.get('valid', False) == True}
        results_invalid = {k: v for k, v in results.items() if v.get('valid', False) == False}

        for k, v in results_valid.items():
            t = Transcript.objects.get(id=k)
            t.valid = True
            t.channel = v['course']
            t.save()

        for k, v in results_invalid.items():
            t = Transcript.objects.get(id=k)
            t.valid = False
            t.channel = v['course']
            t.save()

        cr = CertificateRequest.objects.filter(slack_user_id=slack_user_id).get()
        cr.approved = 'ACC' if request.POST['decision'] == 'ACC' else 'REJ'
        cr.save()
        return redirect('transcript_list', event.id)


    trans = Transcript.objects.filter(slack_user_id=slack_user_id).order_by('-time')
    safetrans = [
        (x.time, x.channel, bleach.clean('\n'.join([f'<a href="{x}">{x}</a>' for x in bleach.clean(x.proof).split()])) , x.id, probably_hist(x.proof), x.valid)
        for x in trans
    ]
    #print(sorted(list(set(sorted([item for sublist in CHANNEL_MAPPING.values() for item in sublist])))))

    # Get their transcript preview
    possible_final = Transcript.objects.filter(slack_user_id=slack_user_id, valid=True)
    final_transcript = {
        t.title: t.ects
        for t in possible_final
    }
    total_ects = sum(final_transcript.values())

    context = {
        'event': event,
        'transcript': safetrans,
        'slack_user_id': slack_user_id,
        'name': get_object_or_404(CertificateRequest, slack_user_id=slack_user_id).human_name,
        'channel_mapping': sorted(list(set(sorted([item for sublist in CHANNEL_MAPPING.values() for item in sublist])))),
        'message': None,
        'final_transcript': final_transcript,
        'total_ects': total_ects,
    }
    return template('transcript.html', request, context)

def mapping(request):
    return JsonResponse(CHANNEL_MAPPING, json_dumps_params={'indent': 2})
