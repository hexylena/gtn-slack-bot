from django.urls import path
from slack_bolt.adapter.django import SlackRequestHandler
from .slack_listeners import app
import os

if 'SLACK_BOT_TOKEN' in os.environ:
    handler = SlackRequestHandler(app=app)
else:
    handler = lambda *a, **kw: print(a, kw)

from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt

from . import views
from csp.decorators import csp_exempt


@csp_exempt
@csrf_exempt
def slack_events_handler(request: HttpRequest):
    return handler.handle(request)


urlpatterns = [
    path('', views.event_list, name='event_list'),
    # path("", views.index, name="index"),
    path('mapping.json', views.mapping, name='mapping'),
    path('dump.tsv', views.dump_tsv, name='dump_tsv'),

    path('e/<int:event_id>/', views.event_home, name='event_home'),
    path('e/<int:event_id>/transcript/', views.transcript_list, name='transcript_list'),
    path('e/<int:event_id>/gratitude/', views.gratitude_list, name='gratitude_list'),
    path('e/<int:event_id>/schedule/', views.schedule_message, name='schedule_message'),
    path('e/<int:event_id>/schedule-single/', views.schedule_message_single, name='schedule_message_single'),
    path('e/<int:event_id>/send-message/<str:channel_id>/', views.send_message_to_channel, name='message'),
    path('e/<int:event_id>/transcript/<str:slack_user_id>/', views.transcript, name='transcript'),
    path("slack/events", slack_events_handler, name="slack_events"),
    path("slack/button", views.slack_button, name="slack_button"),
]
