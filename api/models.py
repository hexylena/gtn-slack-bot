from django.db import models


class Transcript(models.Model):
    slack_user_id = models.CharField(max_length=32)
    time = models.DateTimeField(auto_now_add=True)
    channel = models.TextField()
    proof = models.TextField()


class CertificateRequest(models.Model):
    slack_user_id = models.CharField(max_length=32)
    human_name = models.CharField(max_length=64)
    time = models.DateTimeField(auto_now_add=True)
    course = models.TextField()
    approved = models.TextField()
