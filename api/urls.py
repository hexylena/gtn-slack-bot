from django.urls import path
from slack_bolt.adapter.django import SlackRequestHandler
from .slack_listeners import app

handler = SlackRequestHandler(app=app)

from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt

from . import views


@csrf_exempt
def slack_events_handler(request: HttpRequest):
    return handler.handle(request)


urlpatterns = [
    path("", views.index, name="index"),
    path('mapping.json', views.mapping, name='mapping'),
    path('transcript/', views.transcript_list, name='transcript_list'),
    path('transcript/<str:slack_user_id>/', views.transcript, name='transcript'),
    path("slack/events", slack_events_handler, name="slack_events"),
    path('send-message/<str:channel_id>/', views.send_message_to_channel, name='message'),
]
