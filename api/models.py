from django.db import models
from django.utils import timezone
from api.videolibrary import get_course_name_and_time, parse_time
from django.contrib.auth.models import User


class Event(models.Model):
    name = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Lets certbot automatically start/stop/know when event is over
    start = models.DateTimeField() # Nothing before this date
    end = models.DateTimeField() # End of Joining
    end_grace = models.DateTimeField() # Final day to register a completion

    @property
    def student_count(self):
        return self.slackuser_set.all().count()

    @property
    def organiser_list(self):
        return ', '.join([
            str(u.human_name)
            for u in
            self.eventorganiser_set.all()
        ])

    def __str__(self):
        return self.name


class EventOrganiser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    human_name = models.CharField(max_length=32, null=True)
    slack_user_id = models.CharField(max_length=32, null=True)
    events = models.ManyToManyField(Event)

    @property
    def events_managed(self):
        return ', '.join([
            str(e.name)
            for e in
            self.events.all()
        ])

    def __str__(self):
        return self.human_name


class SlackUser(models.Model):
    slack_user_id = models.CharField(max_length=32)
    # We track the 'current' event which will be used to correctly tag transcripts/etc.
    current_event = models.ForeignKey(Event, null=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slack_user_id


class Transcript(models.Model):
    # Transcripts must still be associated with an event, which we'll copy
    # (dereference) from the slack_user.current_event.
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    slack_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    slack_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # I don't really care if they want different names on each course
    # transcript? Seems safer for folks who prefer different names in different
    # contexts, too.
    human_name = models.CharField(max_length=64)

    CertificateStates = [
        ('ACC', 'Accepted'),
        ('REJ', 'Rejected'),
        ('UNK', 'Unknown'),
        ('S/S', 'Certificate Sent'),
        ('R/S', 'Rejection Sent'),
    ]
    state = models.CharField(max_length=3, choices=CertificateStates, default='UNK')

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

    scheduled_for = models.DateTimeField()
    scheduled_by = models.ForeignKey(EventOrganiser, on_delete=models.CASCADE)

    message = models.TextField()
    sent = models.DateTimeField(null=True, blank=True)

    @property
    def time_until(self):
        return self.scheduled_for - timezone.now()

class Gratitude(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    slack_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)

    message = models.TextField()
    date = models.DateTimeField()
    slack_channel_id = models.CharField(max_length=64)
    slack_channel_name = models.CharField(max_length=64)
