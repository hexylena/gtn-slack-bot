from django.db import models


class Transcript(models.Model):
    slack_user_id = models.CharField(max_length=32)
    time = models.DateTimeField(auto_now_add=True)
    channel = models.TextField()
    proof = models.TextField()
    valid = models.BooleanField(default=False)


class CertificateRequest(models.Model):
    slack_user_id = models.CharField(max_length=32)
    human_name = models.CharField(max_length=64)
    time = models.DateTimeField(auto_now_add=True)
    course = models.TextField()

    CertificateStates = [
        ('ACC', 'Accepted'),
        ('REJ', 'Rejected'),
        ('UNK', 'Unknown')
    ]
    approved = models.CharField(max_length=3, choices=CertificateStates, default='UNK')
