from django.contrib import admin

# Register your models here.
from .models import Transcript, CertificateRequest, ScheduledMessage, Gratitude


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ("slack_user_id", "time", "channel", "proof", "valid")


@admin.register(CertificateRequest)
class CertificateRequestAdmin(admin.ModelAdmin):
    list_display = ("slack_user_id", "time", "human_name", "approved")


@admin.register(ScheduledMessage)
class ScheduledMessageAdmin(admin.ModelAdmin):
    list_display = ("slack_channel_id", "scheduled_for", "sent")
    list_filter = ["slack_channel_id", "sent", "scheduled_for"]


@admin.register(Gratitude)
class GratitudeAdmin(admin.ModelAdmin):
    list_display = ("slack_channel_id", "date", "message")
