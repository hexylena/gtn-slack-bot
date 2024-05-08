from django.contrib import admin

# Register your models here.
from .models import Transcript, CertificateRequest, ScheduledMessage, Gratitude, Event, EventOrganiser, SlackUser


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "start", "end", "end_grace", "student_count", "organiser_list")
    list_filter = ('name',)

@admin.register(EventOrganiser)
class EventOrganiserAdmin(admin.ModelAdmin):
    list_display = ("user", "human_name", "events_managed")
    list_filter = ('user', 'events')


@admin.register(SlackUser)
class SlackUserAdmin(admin.ModelAdmin):
    list_display = ("current_event", "slack_user_id")
    list_filter = ('current_event',)

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('event', "slack_user", "channel", "valid", "title", "ects")
    list_filter = ('event', 'channel', 'valid')


@admin.register(CertificateRequest)
class CertificateRequestAdmin(admin.ModelAdmin):
    list_display = ("event", "slack_user", "human_name", "state", "transcript_count")
    list_filter = ('event',)


@admin.register(ScheduledMessage)
class ScheduledMessageAdmin(admin.ModelAdmin):
    list_display = ("slack_channel_id", "scheduled_for", "sent")
    list_filter = ("slack_channel_id", "sent", "scheduled_for")


@admin.register(Gratitude)
class GratitudeAdmin(admin.ModelAdmin):
    list_display = ("slack_channel_id", "date", "message")
