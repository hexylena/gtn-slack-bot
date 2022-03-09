from django.contrib import admin

# Register your models here.
from .models import Transcript, CertificateRequest


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ("slack_user_id", "time", "channel", "proof")


@admin.register(CertificateRequest)
class CertificateRequestAdmin(admin.ModelAdmin):
    list_display = ("slack_user_id", "time", "human_name", "approved")
