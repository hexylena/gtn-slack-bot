from django.db import models
from django.utils import timezone
from api.videolibrary import get_course_name_and_time, parse_time
from django.contrib.auth.models import User


class Event(models.Model):
    name = models.CharField(max_length=64)
    # Lets certbot automatically start/stop/know when event is over
    start = models.DateTimeField() # Nothing before this date
    end = models.DateTimeField() # End of Joining
    end_grace = models.DateTimeField() # Final day to register a completion


class EventOrganiser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    events = models.ManyToManyField(Event)


class Registration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=32)


class Transcript(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=32)
    time = models.DateTimeField(auto_now_add=True)
    channel = models.TextField()
    proof = models.TextField()
    valid = models.BooleanField(default=False)

    @property
    def title(self):
        return get_course_name_and_time(self.channel)[0]

    @property
    def ects(self):
        t = parse_time(get_course_name_and_time(self.channel)[1])
        try:
            hours = (t.seconds / 3600)
            homework_factor = 1.5
            return round((hours * homework_factor) / 28, 2)
        except:
            print(t, type(t), self.channel)
            return 0

class CertificateRequest(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=32)
    human_name = models.CharField(max_length=64)
    human_name_updated = models.DateTimeField(null=True, blank=True)
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

    @property
    def transcript_count(self):
        return Transcript.objects.filter(slack_user_id=self.slack_user_id, valid=True).count()

    @property
    def transcript_items(self):
        possible_final = Transcript.objects.filter(slack_user_id=self.slack_user_id, valid=True)
        # Deduplicate
        final_transcript = {
            t.title: t.ects
            for t in possible_final
        }
        return final_transcript

    @property
    def total_ects(self):
        possible_final = Transcript.objects.filter(slack_user_id=self.slack_user_id, valid=True)
        # Deduplicate
        final_transcript = {
            t.title: t.ects
            for t in possible_final
        }
        # Sum
        total_ects = sum(final_transcript.values())
        return round(total_ects, 2)

class ScheduledMessage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    slack_channel_id = models.CharField(max_length=32)
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    sent = models.DateTimeField(null=True, blank=True)

    @property
    def time_until(self):
        return self.scheduled_for - timezone.now()

class Gratitude(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    message = models.TextField()
    date = models.DateTimeField()
    slack_channel_id = models.CharField(max_length=64)
