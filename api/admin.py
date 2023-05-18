from django.contrib import admin

# Register your models here.
from .models import Transcript, CertificateRequest, ScheduledMessage


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ("slack_user_id", "time", "channel", "proof", "valid")


@admin.register(CertificateRequest)
class CertificateRequestAdmin(admin.ModelAdmin):
    list_display = ("slack_user_id", "time", "human_name", "approved")


@admin.register(ScheduledMessage)
class ScheduledMessageAdmin(admin.ModelAdmin):
    list_display = ("slack_channel_id", "message", "sent")
    list_filter = ["slack_channel_id", "sent"]
