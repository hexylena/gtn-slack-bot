from django.db import models


#class Event(models.Model):
#    id = models.CharField(max_length=32)
#
#class Registration(models.Model):
#    event = models.ForeignKey('Event')
#    name = models.TextField()
#    email = models.TextField()
#
#class Statistics(models.Model):
#    name = models.CharField(max_length=32)
#    added = models.DateTimeField(auto_now_add=True)


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
        ('UNK', 'Unknown'),
        ('S/S', 'Certificate Sent'),
        ('R/S', 'Rejection Sent'),
    ]
    approved = models.CharField(max_length=3, choices=CertificateStates, default='UNK')

class ScheduledMessage(models.Model):
    slack_channel_id = models.CharField(max_length=32)
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    sent = models.DateTimeField(null=True, blank=True)
