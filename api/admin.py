from django.contrib import admin

# Register your models here.
from .models import Transcript, CertificateRequest

admin.site.register(Transcript)
admin.site.register(CertificateRequest)
